import numpy as np
from sklearn.ensemble import RandomForestClassifier


class UpliftEngine:
    def __init__(self):
        # Model for treated users (received incentive/outreach)
        self.model_treated = RandomForestClassifier(n_estimators=50, random_state=42)
        # Model for control users (no incentive)
        self.model_control = RandomForestClassifier(n_estimators=50, random_state=42)
        self.is_trained = False

    def train_mock_baseline(self):
        """Trains on baseline synthetic SaaS usage features."""
        # Features: [days_inactive, login_frequency, feature_usage_pct, past_support_tickets]
        X_train = np.array([
            [14, 2, 0.1, 3],  # Persuadable candidate
            [2, 25, 0.9, 0],  # Sure thing
            [35, 0, 0.0, 0],  # Sleeping dog
            [30, 1, 0.0, 5],  # Lost cause
        ])

        # Binary outcome: 1 = Retained, 0 = Churned
        y_treated = np.array([1, 1, 0, 0])
        y_control = np.array([0, 1, 1, 0])

        self.model_treated.fit(X_train, y_treated)
        self.model_control.fit(X_train, y_control)
        self.is_trained = True

    def score_user(self, features: list[float]) -> dict:
        """
        Calculates uplift and returns the full causal summary with a FOE metric.
        FOE = Favorable Opportunity Estimate: the uplift signal indicating how much
        the intervention is likely to change retention relative to the control group.
        """
        if not self.is_trained:
            self.train_mock_baseline()

        feat_arr = np.array([features])
        prob_treated = self.model_treated.predict_proba(feat_arr)[0][1]
        prob_control = self.model_control.predict_proba(feat_arr)[0][1]
        uplift_score = prob_treated - prob_control

        # Quadrant logic
        if uplift_score > 0.3:
            quadrant = "Persuadable"
        elif prob_control > 0.7:
            quadrant = "Sure Thing"
        elif prob_treated < 0.2 and prob_control < 0.2:
            quadrant = "Lost Cause"
        else:
            quadrant = "Sleeping Dog"

        return {
            "quadrant": quadrant,
            "uplift_score": float(uplift_score),
            "foe_score": float(uplift_score),
            "prob_treated": float(prob_treated),
            "prob_control": float(prob_control),
            "classification": quadrant,
            "summary": f"{quadrant} with FOE {uplift_score:.3f}",
        }

    def classify_user(self, features: list[float]) -> str:
        """
        Calculates Uplift = P(Retention | Intervened) - P(Retention | Control)
        """
        return self.score_user(features)["quadrant"]

    def classify_user_foe(self, features: list[float]) -> dict:
        """Compatibility helper that returns the full FOE summary for dashboards."""
        return self.score_user(features)
