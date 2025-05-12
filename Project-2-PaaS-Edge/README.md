## Project 2 Summary: Serverless & Edge-Based Face Recognition

**Objective**: Extend the pipeline using AWS Lambda, containerized inference, and eventually offload inference to edge devices using IoT Greengrass.

- **Part I**: Uses Dockerized Lambda functions deployed via AWS ECR. Face detection and recognition are separated into two Lambda functions communicating over SQS.
- **Part II**: Moves face detection to a local (emulated) IoT device running AWS Greengrass Core and communicates with AWS via MQTT and SQS.

**Key Features**:
- Completely serverless design using PaaS
- Efficient inter-function communication using SQS
- Real-time edge inference using Greengrass and secure MQTT messaging
