import torch
import torch.nn as nn
import torchvision.models as models
from PIL import Image
import torchvision.transforms as transforms
import logging

logger = logging.getLogger(__name__)


def load_model(model_path, num_labels):
    """
    Loads a trained EfficientNet-B5 model, ensuring architecture matches the state dict.
    """
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")

    model = models.efficientnet_b5(weights=None)

    in_features = model.classifier[1].in_features
    logger.info(f"Current model's classifier in_features: {in_features}")
    model.classifier[1] = nn.Linear(in_features, num_labels)

    model.load_state_dict(torch.load(model_path, map_location=device), strict=False)

    model.to(device)
    model.eval()
    return model, device


def predict_image(image_path, model, device, label_names, top_k: int = 3):
    """Predict top-k classes for an image using softmax (multi-class setting).

    Args:
        image_path: Path to image file.
        model: Loaded model.
        device: Torch device.
        label_names: List of label names ordered by class index.
        top_k: Number of top classes to return (capped by number of labels).

    Returns:
        top_labels (List[str]): Top-k label names (in descending probability order).
        class_probs (Dict[str, float]): Mapping label -> probability percentage (0~100).
        top_scores (List[float]): Probability percentages for each top label (same order as top_labels).
    """
    transform = transforms.Compose([
        transforms.Resize((456, 456)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    image = Image.open(image_path)
    if image.mode != 'RGB':
        image = image.convert('RGB')

    image_tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(image_tensor)  # shape: [1, C]
        probs = torch.softmax(outputs, dim=1)[0]  # shape: [C]

        k = min(top_k, probs.shape[0])
        top_values, top_indices = probs.topk(k)
        top_labels = [label_names[i] for i in top_indices.tolist()]
        top_scores = [float(v.item()) * 100 for v in top_values]

        class_probs = {label_names[i]: float(probs[i].item()) * 100 for i in range(len(label_names))}

        return top_labels, class_probs, top_scores
