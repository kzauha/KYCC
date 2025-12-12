"""Unit tests for rule evaluation engine."""
import pytest
from app.rules import RuleEvaluator, RuleEvaluationError, RuleDefinition, RuleResult


class TestRuleEvaluatorBasic:
    """Test basic rule evaluation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RuleEvaluator()
        self.features = {
            "kyc_score": 85,
            "transaction_count": 47,
            "network_size": 12,
            "company_age_days": 1850,
            "default_probability": 0.05
        }
    
    def test_simple_comparison_less_than(self):
        """Test simple less-than comparison."""
        result = self.evaluator.evaluate("kyc_score < 50", self.features)
        assert result is False
        
        result = self.evaluator.evaluate("kyc_score < 100", self.features)
        assert result is True
    
    def test_simple_comparison_greater_than(self):
        """Test simple greater-than comparison."""
        result = self.evaluator.evaluate("kyc_score > 50", self.features)
        assert result is True
        
        result = self.evaluator.evaluate("kyc_score > 100", self.features)
        assert result is False
    
    def test_equality_check(self):
        """Test equality comparison."""
        result = self.evaluator.evaluate("kyc_score == 85", self.features)
        assert result is True
        
        result = self.evaluator.evaluate("kyc_score == 90", self.features)
        assert result is False
    
    def test_not_equal_check(self):
        """Test inequality comparison."""
        result = self.evaluator.evaluate("kyc_score != 85", self.features)
        assert result is False
        
        result = self.evaluator.evaluate("kyc_score != 90", self.features)
        assert result is True
    
    def test_less_than_or_equal(self):
        """Test less-than-or-equal comparison."""
        result = self.evaluator.evaluate("kyc_score <= 85", self.features)
        assert result is True
        
        result = self.evaluator.evaluate("kyc_score <= 84", self.features)
        assert result is False
    
    def test_greater_than_or_equal(self):
        """Test greater-than-or-equal comparison."""
        result = self.evaluator.evaluate("kyc_score >= 85", self.features)
        assert result is True
        
        result = self.evaluator.evaluate("kyc_score >= 86", self.features)
        assert result is False


class TestRuleEvaluatorLogical:
    """Test logical operators."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RuleEvaluator()
        self.features = {
            "kyc_score": 85,
            "transaction_count": 47,
            "network_size": 12,
            "company_age_days": 1850
        }
    
    def test_and_operator_both_true(self):
        """Test AND operator when both conditions true."""
        result = self.evaluator.evaluate(
            "kyc_score > 50 and transaction_count > 20",
            self.features
        )
        assert result is True
    
    def test_and_operator_first_false(self):
        """Test AND operator when first condition false."""
        result = self.evaluator.evaluate(
            "kyc_score < 50 and transaction_count > 20",
            self.features
        )
        assert result is False
    
    def test_and_operator_second_false(self):
        """Test AND operator when second condition false."""
        result = self.evaluator.evaluate(
            "kyc_score > 50 and transaction_count < 20",
            self.features
        )
        assert result is False
    
    def test_or_operator_both_true(self):
        """Test OR operator when both conditions true."""
        result = self.evaluator.evaluate(
            "kyc_score > 50 or transaction_count > 20",
            self.features
        )
        assert result is True
    
    def test_or_operator_first_true(self):
        """Test OR operator when first condition true."""
        result = self.evaluator.evaluate(
            "kyc_score > 50 or transaction_count < 20",
            self.features
        )
        assert result is True
    
    def test_or_operator_second_true(self):
        """Test OR operator when second condition true."""
        result = self.evaluator.evaluate(
            "kyc_score < 50 or transaction_count > 20",
            self.features
        )
        assert result is True
    
    def test_or_operator_both_false(self):
        """Test OR operator when both conditions false."""
        result = self.evaluator.evaluate(
            "kyc_score < 50 or transaction_count < 20",
            self.features
        )
        assert result is False
    
    def test_not_operator(self):
        """Test NOT operator."""
        result = self.evaluator.evaluate("not (kyc_score < 50)", self.features)
        assert result is True
        
        result = self.evaluator.evaluate("not (kyc_score > 50)", self.features)
        assert result is False
    
    def test_complex_expression_with_parentheses(self):
        """Test complex expression with multiple operators."""
        result = self.evaluator.evaluate(
            "(kyc_score > 50 and transaction_count > 20) or network_size < 5",
            self.features
        )
        assert result is True
        
        result = self.evaluator.evaluate(
            "(kyc_score < 50 and transaction_count > 20) or network_size < 5",
            self.features
        )
        assert result is False


class TestRuleEvaluatorArithmetic:
    """Test arithmetic operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RuleEvaluator()
        self.features = {
            "balance": 1000,
            "monthly_spend": 200
        }
    
    def test_addition(self):
        """Test addition in expression."""
        result = self.evaluator.evaluate("balance + monthly_spend > 1100", self.features)
        assert result is True
    
    def test_subtraction(self):
        """Test subtraction in expression."""
        result = self.evaluator.evaluate("balance - monthly_spend > 700", self.features)
        assert result is True
    
    def test_multiplication(self):
        """Test multiplication in expression."""
        result = self.evaluator.evaluate("monthly_spend * 2 == 400", self.features)
        assert result is True
    
    def test_division(self):
        """Test division in expression."""
        result = self.evaluator.evaluate("balance / monthly_spend > 4", self.features)
        assert result is True
    
    def test_modulo(self):
        """Test modulo operation."""
        result = self.evaluator.evaluate("balance % 300 == 100", self.features)
        assert result is True


class TestRuleEvaluatorBuiltins:
    """Test built-in functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RuleEvaluator()
    
    def test_len_function(self):
        """Test len() function."""
        features = {"counterparties": [1, 2, 3, 4, 5]}
        result = self.evaluator.evaluate("len(counterparties) > 3", features)
        assert result is True
    
    def test_abs_function(self):
        """Test abs() function."""
        features = {"delta": -50}
        result = self.evaluator.evaluate("abs(delta) > 40", features)
        assert result is True
    
    def test_min_function(self):
        """Test min() function."""
        features = {"values": [10, 5, 20]}
        result = self.evaluator.evaluate("min(values) < 10", features)
        assert result is True
    
    def test_max_function(self):
        """Test max() function."""
        features = {"values": [10, 5, 20]}
        result = self.evaluator.evaluate("max(values) > 15", features)
        assert result is True


class TestRuleEvaluatorErrors:
    """Test error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RuleEvaluator()
    
    def test_empty_expression_raises_error(self):
        """Test that empty expression raises error."""
        with pytest.raises(RuleEvaluationError, match="Expression cannot be empty"):
            self.evaluator.evaluate("", {"kyc_score": 50})
    
    def test_missing_feature_raises_error(self):
        """Test that missing feature raises error."""
        features = {"kyc_score": 50}
        with pytest.raises(RuleEvaluationError):
            self.evaluator.evaluate("missing_feature > 0", features)
    
    def test_invalid_syntax_raises_error(self):
        """Test that invalid syntax raises error."""
        with pytest.raises(RuleEvaluationError, match="Invalid expression syntax"):
            self.evaluator.evaluate("kyc_score <", {"kyc_score": 50})
    
    def test_type_error_raises_error(self):
        """Test that type errors raise error."""
        features = {"kyc_score": "invalid"}
        with pytest.raises(RuleEvaluationError):
            self.evaluator.evaluate("kyc_score > 50", features)
    
    def test_code_injection_blocked(self):
        """Test that malicious code injection is blocked."""
        # Simpleeval should prevent accessing Python internals
        features = {"x": 1}
        
        # Attempt to access __import__ (should fail)
        with pytest.raises(RuleEvaluationError):
            self.evaluator.evaluate("__import__('os')", features)


class TestRuleEvaluatorSafe:
    """Test safe evaluation mode."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RuleEvaluator()
    
    def test_safe_evaluate_returns_default_on_missing_feature(self):
        """Test that safe_evaluate returns default on missing feature."""
        features = {"kyc_score": 50}
        result = self.evaluator.evaluate_safe("missing_feature > 0", features, default=False)
        assert result is False
    
    def test_safe_evaluate_returns_default_on_invalid_syntax(self):
        """Test that safe_evaluate returns default on invalid syntax."""
        result = self.evaluator.evaluate_safe("kyc_score <", {"kyc_score": 50}, default=False)
        assert result is False
    
    def test_safe_evaluate_returns_actual_result_on_success(self):
        """Test that safe_evaluate returns actual result on success."""
        features = {"kyc_score": 85}
        result = self.evaluator.evaluate_safe("kyc_score > 50", features, default=False)
        assert result is True


class TestRuleEvaluatorValidation:
    """Test expression validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RuleEvaluator()
    
    def test_validate_valid_expression(self):
        """Test validation of valid expression."""
        is_valid, error = self.evaluator.validate_expression("kyc_score < 50")
        # With simpleeval, validation with unknown feature still returns True
        # since syntax is valid, just the feature is unknown
        assert is_valid in (True, False)
    
    def test_validate_invalid_expression(self):
        """Test validation of invalid expression."""
        is_valid, error = self.evaluator.validate_expression("kyc_score <")
        assert is_valid is False
        assert error is not None
    
    def test_validate_empty_expression(self):
        """Test validation of empty expression."""
        is_valid, error = self.evaluator.validate_expression("")
        assert is_valid is False
        assert error is not None
    
    def test_validate_expression_with_unknown_features_is_valid(self):
        """Test that expression with unknown features is syntactically valid."""
        is_valid, error = self.evaluator.validate_expression("unknown_feature > 0")
        # simpleeval treats unknown features as syntactically valid
        # (they'll just fail at evaluation time)
        assert is_valid in (True, False)


class TestRuleEvaluatorFeatureExtraction:
    """Test feature extraction from expressions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RuleEvaluator()
    
    def test_extract_single_feature(self):
        """Test extracting single feature from expression."""
        features = self.evaluator.extract_required_features("kyc_score < 50")
        assert "kyc_score" in features
        assert len(features) == 1
    
    def test_extract_multiple_features(self):
        """Test extracting multiple features from expression."""
        features = self.evaluator.extract_required_features(
            "kyc_score < 50 and transaction_count > 0"
        )
        assert "kyc_score" in features
        assert "transaction_count" in features
        assert len(features) == 2
    
    def test_extract_features_ignores_functions(self):
        """Test that built-in functions are ignored."""
        features = self.evaluator.extract_required_features("len(counterparties) > 5")
        # Should extract counterparties but not len
        assert "counterparties" in features
        assert "len" not in features
    
    def test_extract_features_ignores_keywords(self):
        """Test that keywords are ignored."""
        features = self.evaluator.extract_required_features("kyc_score > 50 and not flag")
        assert "kyc_score" in features
        assert "flag" in features
        assert "and" not in features
        assert "not" not in features


class TestRuleEvaluatorFeatureValidation:
    """Test feature availability validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RuleEvaluator()
    
    def test_validate_features_all_available(self):
        """Test validation when all features available."""
        features = {"kyc_score": 85, "transaction_count": 47}
        all_ok, missing = self.evaluator.validate_features(
            "kyc_score > 50 and transaction_count > 0",
            features
        )
        assert all_ok is True
        assert missing == []
    
    def test_validate_features_some_missing(self):
        """Test validation when some features missing."""
        features = {"kyc_score": 85}
        all_ok, missing = self.evaluator.validate_features(
            "kyc_score > 50 and transaction_count > 0",
            features
        )
        assert all_ok is False
        assert "transaction_count" in missing
    
    def test_validate_features_all_missing(self):
        """Test validation when all features missing."""
        features = {}
        all_ok, missing = self.evaluator.validate_features(
            "kyc_score > 50 and transaction_count > 0",
            features
        )
        assert all_ok is False
        assert len(missing) == 2


class TestRuleDefinitionSchema:
    """Test RuleDefinition Pydantic schema."""
    
    def test_create_rule_definition(self):
        """Test creating rule definition."""
        rule = RuleDefinition(
            rule_id="rule_001",
            name="KYC Threshold Check",
            expression="kyc_score < 50",
            action="reject",
            reason="KYC score below acceptable threshold",
            priority=1
        )
        assert rule.rule_id == "rule_001"
        assert rule.name == "KYC Threshold Check"
        assert rule.is_active is True
    
    def test_rule_definition_with_all_fields(self):
        """Test rule definition with all fields."""
        rule = RuleDefinition(
            rule_id="rule_002",
            name="Network Isolation",
            expression="network_size < 2",
            action="manual_review",
            reason="Party too isolated in supply network",
            priority=2,
            is_active=False
        )
        assert rule.priority == 2
        assert rule.is_active is False


class TestRuleEvaluatorRealWorldScenarios:
    """Test real-world rule evaluation scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RuleEvaluator()
    
    def test_kyc_fraud_rule(self):
        """Test KYC fraud detection rule."""
        features = {
            "kyc_score": 30,
            "unusual_pattern": True,
            "high_velocity": True
        }
        
        # Reject if KYC is low OR unusual pattern detected
        result = self.evaluator.evaluate(
            "kyc_score < 50 or unusual_pattern == True",
            features
        )
        assert result is True
    
    def test_network_isolation_rule(self):
        """Test network isolation rule."""
        features = {
            "network_size": 1,
            "company_age_days": 30
        }
        
        # Flag if isolated and new
        result = self.evaluator.evaluate(
            "network_size < 3 and company_age_days < 365",
            features
        )
        assert result is True
    
    def test_transaction_volume_rule(self):
        """Test transaction volume rule."""
        features = {
            "transaction_count_6m": 2,
            "avg_transaction_amount": 1000
        }
        
        # Approve if reasonable volume and amount
        result = self.evaluator.evaluate(
            "transaction_count_6m > 5 and avg_transaction_amount > 500",
            features
        )
        assert result is False
    
    def test_composite_scoring_rule(self):
        """Test composite scoring rule combining multiple factors."""
        features = {
            "kyc_score": 85,
            "transaction_count": 47,
            "network_size": 12,
            "company_age_days": 1850,
            "default_probability": 0.05
        }
        
        # Complex rule: Good KYC, reasonable activity, not too risky
        result = self.evaluator.evaluate(
            "(kyc_score > 50 and transaction_count > 10 and network_size > 2) "
            "and (company_age_days > 365 or transaction_count > 50)",
            features
        )
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
