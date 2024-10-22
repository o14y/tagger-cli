import logging
from pathlib import Path
from typing import Callable, Iterable, List, Optional
from dataclasses import dataclass
from simple_parsing import field, parse_known_args
from PIL import Image
from torch import Tensor, nn
import numpy as np

MODEL_REPO_MAP = {
    'vit': 'SmilingWolf/wd-vit-tagger-v3',
    'swinv2': 'SmilingWolf/wd-swinv2-tagger-v3',
    'convnext': 'SmilingWolf/wd-convnext-tagger-v3',
}

def pil_ensure_rgb(image: Image.Image) -> Image.Image:
    # convert to RGB/RGBA if not already (deals with palette images etc.)
    if image.mode not in ['RGB', 'RGBA']:
        image = image.convert('RGBA') if 'transparency' in image.info else image.convert('RGB')
    # convert RGBA to RGB with white background
    if image.mode == 'RGBA':
        canvas = Image.new('RGBA', image.size, (255, 255, 255))
        canvas.alpha_composite(image)
        image = canvas.convert('RGB')
    return image

def pil_pad_square(image: Image.Image) -> Image.Image:
    w, h = image.size
    # get the largest dimension so we can pad to a square
    px = max(image.size)
    # pad to square with white background
    canvas = Image.new('RGB', (px, px), (255, 255, 255))
    canvas.paste(image, ((px - w) // 2, (px - h) // 2))
    return canvas

@dataclass
class LabelData:
    names: list[str]
    rating: list[np.int64]
    general: list[np.int64]
    character: list[np.int64]

def _load_labels(
    repo_id: str,
    revision: Optional[str] = None,
    token: Optional[str] = None,
) -> LabelData:
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import HfHubHTTPError
    import pandas as pd
    try:
        csv_path = hf_hub_download(
            repo_id=repo_id, filename='selected_tags.csv', revision=revision, token=token
        )
        csv_path = Path(csv_path).resolve()
    except HfHubHTTPError as e:
        raise FileNotFoundError(f'selected_tags.csv failed to download from {repo_id}') from e

    df: pd.DataFrame = pd.read_csv(csv_path, usecols=['name', 'category'])
    tag_data = LabelData(
        names=df['name'].tolist(),
        rating=list(np.where(df['category'] == 9)[0]),
        general=list(np.where(df['category'] == 0)[0]),
        character=list(np.where(df['category'] == 4)[0]),
    )
    return tag_data

def _get_tags(
    probs: Tensor,
    labels: LabelData,
    gen_threshold: float,
    char_threshold: float,
):
    # Convert indices+probs to labels
    probs = list(zip(labels.names, probs.numpy()))

    # First 4 labels are actually ratings
    rating_labels = dict([probs[i] for i in labels.rating])

    # General labels, pick any where prediction confidence > threshold
    gen_labels = [probs[i] for i in labels.general]
    gen_labels = dict([x for x in gen_labels if x[1] > gen_threshold])
    gen_labels = dict(sorted(gen_labels.items(), key=lambda item: item[1], reverse=True))

    # Character labels, pick any where prediction confidence > threshold
    char_labels = [probs[i] for i in labels.character]
    char_labels = dict([x for x in char_labels if x[1] > char_threshold])
    char_labels = dict(sorted(char_labels.items(), key=lambda item: item[1], reverse=True))

    # Combine general and character labels, sort by confidence
    combined_names = [x for x in char_labels]
    combined_names.extend([x.replace('_', ' ') for x in gen_labels])

    # Convert to a string suitable for use as a training caption
    tags = ','.join(combined_names)
    taglist = tags.replace('(', '\\(').replace(')', '\\)')
    return taglist.split(','), taglist, rating_labels, char_labels, gen_labels


def _process_one(image_path: Path, 
                 gen_threshold: float, char_threshold: float, 
                 model: nn.Module, labels: LabelData, transform: Callable, device) -> List[str]:
    import torch
    from torch.nn import functional as F
    log = logging.getLogger(__name__)
    # get image
    img_input: Image.Image = Image.open(image_path)
    # ensure image is RGB
    img_input = pil_ensure_rgb(img_input)
    # pad to square with white background
    img_input = pil_pad_square(img_input)
    # run the model's input transform to convert to tensor and rescale
    inputs: Tensor = transform(img_input).unsqueeze(0)
    # NCHW image RGB to BGR
    inputs = inputs[:, [2, 1, 0]]

    log.info('Running inference...')
    with torch.inference_mode():
        # move model to GPU, if available
        if device.type != 'cpu':
            inputs = inputs.to(device)
        # run the model
        outputs = model.forward(inputs)
        # apply the final activation function (timm doesn't support doing this internally)
        outputs = F.sigmoid(outputs)
        # move inputs, outputs, and model back to to cpu if we were on GPU
        if device.type != 'cpu':
            inputs = inputs.to('cpu')
            outputs = outputs.to('cpu')

    log.info('Processing results...')
    caption, _, _, _, _ = _get_tags(
        probs=outputs.squeeze(0),
        labels=labels,
        gen_threshold=gen_threshold,
        char_threshold=char_threshold,
    )
    return [x.strip() for x in caption]

@dataclass
class InferTagsResult:
    path: Path
    tags: List[str]

def infer_tags(files: List[str],
               model: str="vit", 
               gen_threshold: float = 0.35,
               char_threshold: float = 0.75
               ) -> Iterable[InferTagsResult]:
    import timm
    import torch
    from timm.data import create_transform, resolve_data_config
    import os
    from tqdm import tqdm

    # Check if the provided model is expected
    if model not in MODEL_REPO_MAP:
        raise ValueError(f'Unknown model "{model}". Available models: {list(MODEL_REPO_MAP.keys())}')

    # Use GPU if available
    torch_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Load the model
    log = logging.getLogger(__name__)
    repo_id = MODEL_REPO_MAP.get(model)

    log.info(f'Loading model "{model}" from "{repo_id}"...')
    model: nn.Module = timm.create_model('hf-hub:' + repo_id).eval()
    state_dict = timm.models.load_state_dict_from_hf(repo_id)
    model.load_state_dict(state_dict)

    log.info('Loading tag list...')
    labels: LabelData = _load_labels(repo_id=repo_id)

    log.info('Creating data transform...')
    transform = create_transform(**resolve_data_config(model.pretrained_cfg, model=model))
    files = [Path(f).resolve() for f in files]

    with torch.inference_mode():
        # move model to GPU, if available
        if torch_device.type != 'cpu':
            model = model.to(torch_device)

        import time
        for file in files:
            caption = _process_one(file, gen_threshold, char_threshold, model, labels, transform, torch_device)
            yield InferTagsResult(path=file, tags=caption)

        if torch_device.type != 'cpu':
            model = model.to('cpu')
