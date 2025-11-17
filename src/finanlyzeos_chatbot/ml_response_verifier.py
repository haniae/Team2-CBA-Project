"""Post-processing verification for ML forecast responses to ensure all technical details are included."""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple

LOGGER = logging.getLogger(__name__)


def verify_ml_forecast_response(
    response: str,
    context: str,
    user_input: str
) -> Tuple[bool, List[str], str]:
    """
    Verify if ML forecast response includes all required technical details.
    
    Returns:
        (is_complete, missing_details, enhanced_response)
    """
    try:
        from .context_builder import _is_forecasting_query
        if not _is_forecasting_query(user_input):
            return True, [], response  # Not a forecasting query, skip verification
    except ImportError:
        return True, [], response
    
    # Check if context contains ML forecast data
    if "ML FORECAST" not in context and "CRITICAL: THIS IS THE PRIMARY ANSWER" not in context:
        return True, [], response  # No ML forecast context, skip verification
    
    missing_details = []
    response_lower = response.lower()
    
    # Check if EXPLICIT DATA DUMP section exists in context
    has_explicit_dump = "EXPLICIT DATA DUMP" in context
    
    # Required details to check - expanded list
    required_checks = [
        # Model architecture
        ("layers", ["layer", "architecture", "network"]),
        ("units", ["unit", "neuron", "hidden"]),
        ("total_parameters", ["parameter", "param"]),
        ("input_shape", ["input", "shape"]),
        ("num_layers", ["transformer", "encoder layer", "num layer"]),
        ("num_heads", ["attention head", "head", "multi-head"]),
        ("d_model", ["model dimension", "embedding dimension", "d_model"]),
        ("dim_feedforward", ["feedforward", "ff dimension"]),
        
        # Training details
        ("epochs_trained", ["epoch", "trained", "training epoch"]),
        ("training_loss", ["training loss", "train loss", "mse", "mean squared error"]),
        ("validation_loss", ["validation loss", "val loss", "validation mse"]),
        ("overfit_ratio", ["overfit", "overfitting", "val/train", "validation/training"]),
        
        # Hyperparameters
        ("learning_rate", ["learning rate", "lr", "learning_rate"]),
        ("batch_size", ["batch size", "batch", "batch_size"]),
        ("optimizer", ["optimizer", "adam", "sgd", "rmsprop", "adagrad"]),
        ("dropout", ["dropout", "dropout rate"]),
        ("lookback_window", ["lookback", "window", "lookback window"]),
        
        # Computational details
        ("training_time", ["training time", "train time", "training duration"]),
        ("data_points_used", ["data point", "period", "sample", "data point", "historical data"]),
        ("train_test_split", ["train/test", "split", "train test split"]),
        
        # Preprocessing
        ("scaling_method", ["scaling", "scaler", "normalize", "standardize", "minmax"]),
        ("preprocessing_applied", ["preprocessing", "feature engineering"]),
        
        # ARIMA specific
        ("arima_order", ["arima order", "p,d,q", "ar order", "ma order", "differencing"]),
        ("aic", ["aic", "akaike"]),
        ("bic", ["bic", "bayesian"]),
        
        # Prophet specific
        ("changepoint_count", ["changepoint", "trend change"]),
        ("growth_model", ["growth model", "linear growth", "logistic growth"]),
        
        # ETS specific
        ("ets_model_type", ["ets model", "ets type", "error trend seasonal"]),
        ("smoothing_params", ["smoothing", "alpha", "beta", "gamma"]),
        
        # Growth rates
        ("growth_rate", ["growth", "yoy", "year-over-year", "year over year"]),
        ("cagr", ["cagr", "compound", "compound annual growth"]),
    ]
    
    # Extract values from context - prioritize EXPLICIT DATA DUMP section
    context_values = _extract_values_from_context(context)
    
    # If EXPLICIT DATA DUMP exists, be more strict about checking
    strict_mode = has_explicit_dump
    
    # Check if each required detail is mentioned in response
    for key, keywords in required_checks:
        if key in context_values:
            # Check if any keyword is mentioned
            found = any(keyword in response_lower for keyword in keywords)
            if not found:
                # In strict mode (EXPLICIT DATA DUMP exists), require exact value match too
                if strict_mode:
                    # Check if the exact value is mentioned (even if keyword isn't)
                    value = str(context_values[key])
                    value_found = value in response or value.replace(',', '') in response.replace(',', '')
                    if not value_found:
                        missing_details.append(f"{key}: {context_values[key]}")
                else:
                    missing_details.append(f"{key}: {context_values[key]}")
    
    # If missing details, enhance response
    if missing_details:
        LOGGER.warning(f"ML forecast response missing {len(missing_details)} required details")
        enhanced_response = _enhance_response_with_missing_details(
            response, missing_details, context_values
        )
        return False, missing_details, enhanced_response
    
    return True, [], response


def _extract_values_from_context(context: str) -> Dict[str, Any]:
    """Extract technical detail values from context."""
    values = {}
    
    # Extract from "FINAL CHECKLIST" or "EXPLICIT DATA DUMP" section
    checklist_match = re.search(
        r"(?:FINAL CHECKLIST|EXPLICIT DATA DUMP|MODEL TECHNICAL DETAILS).*?\n(.*?)(?=\n={80}|\Z)",
        context,
        re.DOTALL | re.IGNORECASE
    )
    if checklist_match:
        checklist_text = checklist_match.group(1)
        
        # Extract specific values with more flexible patterns
        patterns = {
            "layers": [
                r"Network Architecture.*?(\d+)\s+layers",
                r"layers.*?(\d+)",
                r"(\d+)\s+layers",
            ],
            "units": [
                r"Hidden Units per Layer.*?(\d+)",
                r"units.*?(\d+)",
                r"(\d+)\s+units",
            ],
            "total_parameters": [
                r"Total Parameters.*?([\d,]+)",
                r"parameters.*?([\d,]+)",
            ],
            "epochs_trained": [
                r"Training Epochs.*?(\d+)",
                r"epochs.*?(\d+)",
                r"trained.*?(\d+)\s+epochs",
            ],
            "training_loss": [
                r"Training Loss.*?([\d.]+)",
                r"training loss.*?([\d.]+)",
            ],
            "validation_loss": [
                r"Validation Loss.*?([\d.]+)",
                r"validation loss.*?([\d.]+)",
            ],
            "learning_rate": [
                r"Learning Rate.*?([\d.]+)",
                r"learning rate.*?([\d.]+)",
            ],
            "batch_size": [
                r"Batch Size.*?(\d+)",
                r"batch size.*?(\d+)",
            ],
            "optimizer": [
                r"Optimizer.*?(\w+)",
                r"optimizer.*?(\w+)",
            ],
            "dropout": [
                r"Dropout Rate.*?([\d.]+)",
                r"dropout.*?([\d.]+)",
            ],
            "training_time": [
                r"Training Time.*?([\d.]+)",
                r"training time.*?([\d.]+)",
            ],
            "data_points_used": [
                r"Data Points Used.*?(\d+)",
                r"data points.*?(\d+)",
            ],
            "scaling_method": [
                r"Scaling Method.*?(\w+)",
                r"scaling.*?(\w+)",
            ],
        }
        
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, checklist_text, re.IGNORECASE)
                if match:
                    values[key] = match.group(1)
                    break
    
    # Also extract from any section with model details
    # Look for key-value pairs in the format "- **Key:** Value"
    detail_pattern = r"- \*\*([^*]+):\*\* ([^\n]+)"
    for match in re.finditer(detail_pattern, context, re.IGNORECASE):
        key = match.group(1).strip().lower().replace(" ", "_")
        value = match.group(2).strip()
        
        # Map common key variations
        key_mapping = {
            "network_architecture": "layers",
            "hidden_units_per_layer": "units",
            "total_parameters": "total_parameters",
            "training_epochs": "epochs_trained",
            "training_loss_(mse)": "training_loss",
            "validation_loss_(mse)": "validation_loss",
            "learning_rate": "learning_rate",
            "batch_size": "batch_size",
            "optimizer": "optimizer",
            "dropout_rate": "dropout",
            "training_time": "training_time",
            "data_points_used": "data_points_used",
            "scaling_method": "scaling_method",
        }
        
        for mapped_key, standard_key in key_mapping.items():
            if mapped_key in key:
                if standard_key not in values:
                    values[standard_key] = value
                break
    
    return values


def _enhance_response_with_missing_details(
    response: str,
    missing_details: List[str],
    context_values: Dict[str, Any]
) -> str:
    """Enhance response by appending missing technical details."""
    
    # Find where to insert (before Sources section if it exists)
    sources_match = re.search(r"\n📊\s*Sources?:", response, re.IGNORECASE)
    insert_position = sources_match.start() if sources_match else len(response)
    
    # Build missing details section
    missing_section = "\n\n## 🔧 Additional Technical Details\n\n"
    missing_section += "**The following technical specifications were not fully detailed in the response above:**\n\n"
    
    # Group missing details by category
    architecture = []
    training = []
    hyperparams = []
    computational = []
    other = []
    
    for detail in missing_details:
        key, value = detail.split(": ", 1)
        if key in ["layers", "units", "total_parameters", "input_shape"]:
            architecture.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        elif key in ["epochs_trained", "training_loss", "validation_loss", "overfit_ratio"]:
            training.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        elif key in ["learning_rate", "batch_size", "optimizer", "dropout", "lookback_window"]:
            hyperparams.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        elif key in ["training_time", "data_points_used", "train_test_split"]:
            computational.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        else:
            other.append(f"- **{key.replace('_', ' ').title()}:** {value}")
    
    if architecture:
        missing_section += "### Model Architecture\n"
        missing_section += "\n".join(architecture) + "\n\n"
    
    if training:
        missing_section += "### Training Details\n"
        missing_section += "\n".join(training) + "\n\n"
    
    if hyperparams:
        missing_section += "### Hyperparameters\n"
        missing_section += "\n".join(hyperparams) + "\n\n"
    
    if computational:
        missing_section += "### Computational Details\n"
        missing_section += "\n".join(computational) + "\n\n"
    
    if other:
        missing_section += "### Other Details\n"
        missing_section += "\n".join(other) + "\n\n"
    
    # Insert missing section
    enhanced_response = (
        response[:insert_position] + 
        missing_section + 
        response[insert_position:]
    )
    
    return enhanced_response

