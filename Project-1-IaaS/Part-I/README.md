# Project 1 – Part I: IaaS – Web Tier with SimpleDB

This part implements a web-tier EC2 instance that accepts image uploads via HTTP, stores them in S3, and performs face recognition using a SimpleDB lookup.

## Architecture
- **Frontend:** Python Flask server on EC2
- **Storage:** Amazon S3
- **Emulated Recognition:** AWS SimpleDB (lookup table)

## Features
- Handles concurrent image uploads
- Stores files in `<ASUID>-in-bucket`
- Queries SimpleDB to get predicted labels

## Setup
- Launch EC2 micro instance in `us-east-1`
- Assign Elastic IP and name instance `web-instance`
- Use `server.py` to handle POST requests on port 8000
