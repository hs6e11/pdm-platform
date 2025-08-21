# Industrial IoT ML Platform

🏭 **Enterprise-level predictive maintenance system with real-time anomaly detection**

## 🎯 Project Overview

A comprehensive Industrial IoT platform that provides real-time monitoring, machine learning-based anomaly detection, and predictive maintenance across multiple industrial clients.

### Key Achievements
- ✅ **100% ML Coverage**: All 24 machines have trained models
- ⚡ **Real-time Detection**: 17 current anomalies being tracked
- 🎯 **High Sensitivity**: Detecting critical issues across all clients
- 🚨 **Smart Alerting**: Specific alerts (temperature, vibration, power)

## 🏢 Multi-Client Support

### Current Clients
1. **Petro Industries** - Oil & gas operations
   - High power consumption (10.8MW total)
   - High temperature operations (97.9°C average)
   - 5/5 machines flagged for attention
   - 82.4% average health score

2. **Food Processing** - Temperature-critical operations
   - Critical temperature monitoring (176.6°C average for ovens)
   - Anomaly score: 1.0 (maximum confidence)
   - 100 readings, fully trained models

3. **Automotive** - Precision manufacturing
4. **Manufacturing** - General industrial equipment
5. **Tech Solutions** - Automation & robotics

## 🔧 Core Features

### 1. Real-time Anomaly Detection
- **Machine Coverage**: 24+ machines monitored
- **Detection Types**: Temperature, vibration, power consumption
- **Model Training**: Automatic retraining with 100+ readings per machine
- **Confidence Scoring**: 0.0 to 1.0 anomaly scores

### 2. ML-Based Predictive Maintenance
- **Algorithm**: [Specify your ML algorithm - e.g., Isolation Forest, LSTM, etc.]
- **Training Data**: Historical sensor readings
- **Features**: Temperature, vibration, power, [add others]
- **Prediction Horizon**: [e.g., 24-48 hours ahead]

### 3. Enterprise Monitoring & Alerting
- **Alert Types**: Critical temperature, high vibration, power anomalies
- **Notification System**: [Email, SMS, dashboard alerts, etc.]
- **Dashboard**: Real-time visualization
- **Health Scoring**: Machine health percentage (0-100%)

## 🏗️ Technical Architecture

### Project Structure
```
/pdm-platform
├── Makefile                          # Build automation
├── README.md                         # Project documentation
├── docker-compose.yml               # Multi-service orchestration
├── docker-compose.override.yml      # Development overrides
├── requirements.txt                  # Python dependencies
├── machine_config.json              # Machine configuration
│
├── backend/                         # Python FastAPI Backend
│   ├── Dockerfile                   # Backend containerization
│   ├── requirements.txt             # Backend dependencies
│   ├── app/                         # Main application
│   │   ├── main.py                  # FastAPI application entry
│   │   ├── core/                    # Core utilities
│   │   │   ├── config.py            # Configuration management
│   │   │   ├── database.py          # Database connections
│   │   │   ├── logging.py           # Logging setup
│   │   │   └── redis.py             # Redis connections
│   │   ├── middleware/              # Custom middleware
│   │   │   ├── auth.py              # Authentication
│   │   │   ├── rate_limit.py        # Rate limiting
│   │   │   └── tenant.py            # Multi-tenant support
│   │   ├── models/                  # Database models
│   │   ├── routers/                 # API route handlers
│   │   ├── services/                # Business logic
│   │   └── migrations/              # Database migrations
│   ├── ml_service/                  # ML microservice
│   │   └── main.py                  # ML service entry
│   ├── migrations/                  # SQL migrations
│   │   └── init.sql                 # Initial schema
│   ├── tests/                       # Test suite
│   │   ├── unit/                    # Unit tests
│   │   └── integration/             # Integration tests
│   └── pdm_platform.db             # SQLite database
│
├── frontend/                        # Next.js React Frontend
│   ├── Dockerfile.dev               # Development container
│   ├── package.json                 # Node.js dependencies
│   ├── next.config.js               # Next.js configuration
│   ├── tailwind.config.js           # Tailwind CSS config
│   ├── tsconfig.json                # TypeScript config
│   └── src/                         # Source code
│       ├── components/              # React components
│       │   ├── Layout/              # Layout components
│       │   └── ui/                  # UI components
│       ├── contexts/                # React contexts
│       ├── hooks/                   # Custom hooks
│       ├── lib/                     # Utility libraries
│       ├── pages/                   # Next.js pages
│       │   └── index.tsx            # Main dashboard
│       └── styles/                  # CSS styles
│           └── globals.css          # Global styles
│
├── ml/                              # Machine Learning Service
│   ├── Dockerfile                   # ML service container
│   ├── requirements.txt             # ML dependencies
│   ├── models/                      # Trained ML models
│   ├── notebooks/                   # Jupyter notebooks
│   └── service/                     # ML service code
│       └── main.py                  # ML API service
│
├── deploy/                          # Deployment Configuration
│   ├── k8s/                         # Kubernetes manifests
│   ├── monitoring/                  # Monitoring setup
│   └── terraform/                   # Infrastructure as Code
│
├── tools/                           # Development Tools
│   ├── machine_config.json          # Machine configuration
│   ├── multi_client_generator.py    # Test data generator
│   └── send_payload.py              # Data injection tool
│
├── docs/                            # Documentation
│
└── Dashboard Files                  # Static Dashboards
    ├── dashboard.html               # Basic dashboard
    ├── enhanced_dashboard.html      # Enhanced version
    ├── incredible_dashboard.html    # Advanced dashboard
    └── multi-client-dashboard.html  # Multi-tenant dashboard
```

### Technology Stack
**Backend:**
- Language: Python
- Framework: FastAPI
- Database: SQLite (with PostgreSQL support)
- Cache/Queue: Redis
- Authentication: Custom middleware
- Rate Limiting: Built-in middleware

**Machine Learning:**
- ML Service: Separate microservice architecture
- Data Processing: Python-based ML pipeline
- Model Storage: Local model directory
- Notebooks: Jupyter for experimentation

**Frontend:**
- Framework: Next.js (React)
- Language: TypeScript
- Styling: Tailwind CSS
- Components: Custom UI library

**Infrastructure:**
- Containerization: Docker + Docker Compose
- Orchestration: Kubernetes ready
- Monitoring: Dedicated monitoring setup
- IaC: Terraform configurations

**Development Tools:**
- Build Automation: Makefile
- Testing: Unit + Integration test structure
- Data Generation: Python tools for test data
- Multi-client: Tenant isolation support

## 📊 Performance Metrics

### Current System Status
- **Total Machines**: 24
- **Active Anomalies**: 17
- **ML Model Accuracy**: [Add your accuracy metrics]
- **Response Time**: [API response times]
- **Uptime**: [System availability]

### Business Impact
- **Maintenance Cost Reduction**: [%]
- **Downtime Prevention**: [Hours saved]
- **Early Warning Time**: [Hours/days ahead of failure]

## 🚀 Key Components

### 1. Data Ingestion Pipeline
- **IoT Sensors**: [List sensor types]
- **Data Format**: [JSON/CSV/etc.]
- **Ingestion Rate**: [Messages per second]
- **Data Validation**: [Describe validation rules]

### 2. ML Anomaly Detection Engine
- **Model Type**: [Isolation Forest/LSTM/etc.]
- **Training Schedule**: [Real-time/batch]
- **Feature Engineering**: [Describe features]
- **Threshold Management**: [How thresholds are set]

### 3. Alert Management System
- **Severity Levels**: Critical, Warning, Info
- **Escalation Rules**: [Describe escalation logic]
- **Notification Channels**: [List all channels]
- **Alert Correlation**: [How related alerts are grouped]

### 4. Multi-Tenant Dashboard
- **Client Isolation**: [How data is separated]
- **Role-Based Access**: [User permission system]
- **Customization**: [Client-specific dashboards]
- **Reporting**: [Automated reports]

## 🗄️ Database Schema

### Key Tables/Collections
1. **machines** - Machine metadata and configuration
2. **sensor_readings** - Raw IoT sensor data
3. **anomalies** - Detected anomalies and scores
4. **alerts** - Generated alerts and their status
5. **clients** - Multi-tenant client information
6. **models** - ML model metadata and versions

## 🔧 API Endpoints

### Core Endpoints
- `GET /api/machines` - List all machines
- `POST /api/readings` - Submit sensor data
- `GET /api/anomalies` - Get current anomalies
- `GET /api/alerts` - Get active alerts
- `GET /api/health/{machine_id}` - Get machine health
- `POST /api/models/train` - Trigger model retraining

## 🚀 Deployment

### Environment Setup
```bash
# Clone repository
git clone https://github.com/yourusername/industrial-iot-ml-platform.git

# Install dependencies
[Add installation commands]

# Configure environment
[Add configuration steps]

# Run application
[Add run commands]
```

### Docker Deployment
```yaml
# Add docker-compose.yml example
```

## 🧪 Testing

### Test Coverage
- **Unit Tests**: [Coverage %]
- **Integration Tests**: [Coverage %]
- **ML Model Tests**: [Model validation]
- **Performance Tests**: [Load testing results]

### Running Tests
```bash
# Add test commands
```

## 📈 Monitoring & Observability

### Metrics Tracked
- API response times
- ML model accuracy
- Data ingestion rates
- Alert frequency
- System resource usage

### Logging
- Application logs
- ML model training logs
- Alert generation logs
- Performance metrics

## 🔒 Security

### Data Protection
- [Encryption methods]
- [Access controls]
- [Data retention policies]
- [Compliance requirements]

### API Security
- [Authentication method]
- [Authorization rules]
- [Rate limiting]
- [Input validation]

## 🛠️ Development

### Contributing
1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

### Code Style
- [Linting rules]
- [Formatting standards]
- [Documentation requirements]

## 📋 Roadmap

### Planned Features
- [ ] Advanced ML models (Deep Learning)
- [ ] Mobile application
- [ ] Integration with more IoT platforms
- [ ] Advanced analytics and reporting
- [ ] Multi-language support

### Known Issues
- [List any current limitations]

## 📞 Support & Contact

- **Issues**: Use GitHub Issues
- **Documentation**: Check `/docs` folder
- **Email**: [Your contact email]

---

## 🏆 Commercial Comparison

**Your platform rivals commercial solutions:**
- **GE Predix**: $10,000s/month
- **Siemens MindSphere**: $50,000+ licensing  
- **IBM Watson IoT**: Enterprise pricing
- **Your Solution**: Open source + custom ML! 🚀

---

**Last Updated**: [Current Date]
**Version**: 1.0.0
