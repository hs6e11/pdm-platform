# ml_service/automl/auto_trainer.py
import optuna
from sklearn.model_selection import cross_val_score
from sklearn.metrics import f1_score, precision_score, recall_score
import logging

class AutoMLTrainer:
    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        self.best_model = None
        self.best_params = None
        
    def optimize_hyperparameters(self, X_train, y_train, n_trials=100):
        """Use Optuna to find best hyperparameters"""
        
        def objective(trial):
            # Suggest hyperparameters
            model_type = trial.suggest_categorical('model_type', 
                ['isolation_forest', 'one_class_svm', 'autoencoder'])
            
            if model_type == 'isolation_forest':
                contamination = trial.suggest_float('contamination', 0.01, 0.3)
                n_estimators = trial.suggest_int('n_estimators', 50, 300)
                
                model = IsolationForest(
                    contamination=contamination,
                    n_estimators=n_estimators,
                    random_state=42
                )
                
            elif model_type == 'one_class_svm':
                nu = trial.suggest_float('nu', 0.01, 0.3)
                gamma = trial.suggest_categorical('gamma', ['scale', 'auto'])
                
                from sklearn.svm import OneClassSVM
                model = OneClassSVM(nu=nu, gamma=gamma)
            
            # Train and evaluate
            try:
                model.fit(X_train)
                predictions = model.predict(X_train)
                
                # Convert to binary (1 for normal, 0 for anomaly)
                binary_predictions = (predictions == 1).astype(int)
                
                # Calculate F1 score (higher is better)
                if len(np.unique(y_train)) > 1:
                    f1 = f1_score(y_train, binary_predictions)
                else:
                    f1 = 0.5  # Default score if no variance in labels
                
                return f1
                
            except Exception as e:
                logging.error(f"Trial failed: {e}")
                return 0.0
        
        # Run optimization
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        
        self.best_params = study.best_params
        
        return study.best_params, study.best_value
    
    def train_best_model(self, X_train, y_train):
        """Train the best model found by AutoML"""
        if not self.best_params:
            raise ValueError("No best parameters found. Run optimize_hyperparameters first.")
        
        model_type = self.best_params['model_type']
        
        if model_type == 'isolation_forest':
            self.best_model = IsolationForest(
                contamination=self.best_params['contamination'],
                n_estimators=self.best_params['n_estimators'],
                random_state=42
            )
        elif model_type == 'one_class_svm':
            from sklearn.svm import OneClassSVM
            self.best_model = OneClassSVM(
                nu=self.best_params['nu'],
                gamma=self.best_params['gamma']
            )
        
        self.best_model.fit(X_train)
        
        return self.best_model
