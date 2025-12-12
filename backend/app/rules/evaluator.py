"""Safe rule evaluation engine using simpleeval."""
from typing import Dict, Any, List, Optional
from simpleeval import simple_eval, FeatureNotAvailable, NameNotDefined
import logging

logger = logging.getLogger(__name__)


class RuleEvaluationError(Exception):
    """Raised when rule evaluation fails."""
    pass


class RuleEvaluator:
    """
    Safe rule expression evaluator using simpleeval.
    
    Evaluates decision rule expressions in a sandboxed environment without
    allowing code execution or access to Python internals.
    
    Supported operations:
    - Comparisons: <, >, <=, >=, ==, !=
    - Logical: and, or, not
    - Arithmetic: +, -, *, /, %, **
    - Membership: in, not in
    - Parentheses for grouping
    
    Example:
        >>> evaluator = RuleEvaluator()
        >>> features = {"kyc_score": 30, "transaction_count": 5}
        >>> result = evaluator.evaluate("kyc_score < 50", features)
        >>> print(result)
        True
    """
    
    def __init__(self):
        """Initialize rule evaluator."""
        self.functions = {
            "len": len,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
        }
    
    def evaluate(self, expression: str, features: Dict[str, Any]) -> bool:
        """
        Safely evaluate a rule expression against features.
        
        Args:
            expression: Rule expression (e.g., "kyc_score < 50 AND transaction_count > 0")
            features: Feature dictionary (e.g., {"kyc_score": 85, "transaction_count": 47})
        
        Returns:
            Boolean result of expression evaluation
        
        Raises:
            RuleEvaluationError: If expression is invalid or evaluation fails
        
        Example:
            >>> evaluator = RuleEvaluator()
            >>> features = {"kyc_score": 85, "transaction_count": 47}
            >>> evaluator.evaluate("kyc_score > 50 and transaction_count > 20", features)
            True
        """
        if not expression or not expression.strip():
            raise RuleEvaluationError("Expression cannot be empty")
        
        try:
            result = simple_eval(
                expression,
                names=features,
                functions=self.functions
            )
            return bool(result)
        except (FeatureNotAvailable, NameNotDefined) as e:
            # Missing feature in features dict
            missing_feature = str(e).split("'")[1] if "'" in str(e) else "unknown"
            raise RuleEvaluationError(
                f"Feature '{missing_feature}' not available in features dict. "
                f"Available: {list(features.keys())}"
            )
        except SyntaxError as e:
            raise RuleEvaluationError(f"Invalid expression syntax: {e}")
        except TypeError as e:
            raise RuleEvaluationError(f"Type error in expression: {e}")
        except Exception as e:
            raise RuleEvaluationError(f"Failed to evaluate expression: {type(e).__name__}: {e}")
    
    def evaluate_safe(self, expression: str, features: Dict[str, Any], default: bool = False) -> bool:
        """
        Safely evaluate a rule expression with fallback on error.
        
        Unlike evaluate(), this method returns a default value on error
        instead of raising an exception. Useful for non-critical rules.
        
        Args:
            expression: Rule expression
            features: Feature dictionary
            default: Value to return if evaluation fails (default: False)
        
        Returns:
            Boolean result of expression, or default if evaluation fails
        
        Example:
            >>> evaluator = RuleEvaluator()
            >>> features = {"kyc_score": 85}
            >>> # Missing 'missing_feature' won't raise, just returns False
            >>> evaluator.evaluate_safe("kyc_score > 50 and missing_feature", features, default=False)
            False
        """
        try:
            return self.evaluate(expression, features)
        except RuleEvaluationError as e:
            logger.warning(f"Rule evaluation failed, using default: {e}")
            return default
    
    def validate_expression(self, expression: str) -> tuple[bool, Optional[str]]:
        """
        Validate rule expression syntax without evaluating against features.
        
        Args:
            expression: Rule expression to validate
        
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if syntax is correct
            - error_message: Error description if invalid, None otherwise
        
        Example:
            >>> evaluator = RuleEvaluator()
            >>> is_valid, error = evaluator.validate_expression("kyc_score < 50")
            >>> print(is_valid)
            True
            
            >>> is_valid, error = evaluator.validate_expression("kyc_score <")
            >>> print(is_valid, error)
            False 'invalid syntax...'
        """
        if not expression or not expression.strip():
            return False, "Expression cannot be empty"
        
        try:
            # Try evaluating with dummy features
            dummy_features = {"dummy": 0}
            simple_eval(expression, names=dummy_features, functions=self.functions)
            return True, None
        except (FeatureNotAvailable, NameNotDefined):
            # Expression is syntactically valid, just references unknown feature
            return True, None
        except SyntaxError as e:
            return False, f"Invalid syntax: {e}"
        except Exception as e:
            return False, f"Validation error: {type(e).__name__}: {e}"
    
    def extract_required_features(self, expression: str) -> List[str]:
        """
        Extract feature names required by a rule expression.
        
        Args:
            expression: Rule expression
        
        Returns:
            List of feature names referenced in expression
        
        Example:
            >>> evaluator = RuleEvaluator()
            >>> features = evaluator.extract_required_features("kyc_score < 50 and transaction_count > 0")
            >>> print(features)
            ['kyc_score', 'transaction_count']
        """
        required = set()
        
        # Try evaluating with a feature tracker
        import re
        
        # Simple regex to find variable names (alphanumeric + underscore)
        # This is not perfect but works for most cases
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        
        # Find all potential variables
        potential_vars = set(re.findall(pattern, expression))
        
        # Filter out Python keywords and function names
        keywords = {'and', 'or', 'not', 'in', 'len', 'min', 'max', 'abs', 'round', 'True', 'False', 'None'}
        required = potential_vars - keywords
        
        return sorted(list(required))
    
    def validate_features(self, expression: str, features: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Check if all required features are available in feature dict.
        
        Args:
            expression: Rule expression
            features: Available features
        
        Returns:
            Tuple of (all_available, missing_features)
            - all_available: True if all features are present
            - missing_features: List of missing feature names
        
        Example:
            >>> evaluator = RuleEvaluator()
            >>> features = {"kyc_score": 85}
            >>> all_ok, missing = evaluator.validate_features("kyc_score < 50 and transaction_count > 0", features)
            >>> print(all_ok, missing)
            False ['transaction_count']
        """
        required = self.extract_required_features(expression)
        available = set(features.keys())
        missing = [f for f in required if f not in available]
        
        return len(missing) == 0, missing


# Global evaluator instance (singleton pattern)
_global_evaluator = None


def get_evaluator() -> RuleEvaluator:
    """
    Get global rule evaluator instance.
    
    Returns:
        Singleton RuleEvaluator instance
    
    Example:
        >>> evaluator = get_evaluator()
        >>> result = evaluator.evaluate("kyc_score < 50", {"kyc_score": 30})
    """
    global _global_evaluator
    if _global_evaluator is None:
        _global_evaluator = RuleEvaluator()
    return _global_evaluator
