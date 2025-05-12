## 🔹 Project 1 Summary: IaaS-Based Face Recognition

**Objective**: Build a scalable face recognition web app using EC2, S3, and SimpleDB. In Part II, introduce autoscaling with multiple app-tier instances.

- **Part I**: Implements a web-tier Flask app on a single EC2 instance that accepts images, stores them in S3, and uses SimpleDB as a mock inference engine.
- **Part II**: Adds an app tier that uses a real PyTorch model, processes requests from SQS, and automatically scales EC2 instances using a custom autoscaling controller.

**Key Features**:
- Multi-tier architecture (web + app tiers)
- Manual autoscaling using Python logic
- End-to-end image processing pipeline using AWS primitives only (no Auto Scaling Group)
