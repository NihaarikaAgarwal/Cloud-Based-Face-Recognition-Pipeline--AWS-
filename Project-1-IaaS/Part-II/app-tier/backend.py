import boto3
import os
import subprocess

REGION = "us-east-1"
ASU_ID = ""  
S3_INPUT_BUCKET = f"{ASU_ID}-in-bucket"
S3_OUTPUT_BUCKET = f"{ASU_ID}-out-bucket"
SQS_REQUEST_QUEUE = f"{ASU_ID}-req-queue"
SQS_RESPONSE_QUEUE = f"{ASU_ID}-resp-queue"

MODEL_DIR= "/home/ec2-user/CSE546-SPRING-2025-model" 

s3 = boto3.client('s3', region_name=REGION)
sqs = boto3.client('sqs', region_name=REGION)

LOCAL_IMAGE_PATH = "/tmp/"  

def process_image(image_name):
    local_image = os.path.join(LOCAL_IMAGE_PATH, image_name)
    print(S3_INPUT_BUCKET, image_name, local_image)
    s3.download_file(S3_INPUT_BUCKET, image_name, local_image)

    try:
        result = subprocess.run(
                ["python3", "face_recognition.py", local_image], 
                capture_output=True, 
                text=True,
                check=True,
                cwd=MODEL_DIR  
            )

        prediction = result.stdout.strip()  
    except subprocess.CalledProcessError as e:
        prediction = f"Error: {e.stderr.strip()}"

    print(f"Inference result: {prediction}")

    
    result_key = image_name.split('.')[0]  
    s3.put_object(Bucket=S3_OUTPUT_BUCKET, Key=result_key, Body=prediction)

    response_queue_url = sqs.get_queue_url(QueueName=SQS_RESPONSE_QUEUE)['QueueUrl']
    sqs.send_message(QueueUrl=response_queue_url, MessageBody=f"{result_key}:{prediction}")

    os.remove(local_image)
    print(f"Processed and removed {local_image}.")

def main():
    
    request_queue_url = sqs.get_queue_url(QueueName=SQS_REQUEST_QUEUE)['QueueUrl']
    
    while True:
        
        msgs = sqs.receive_message(QueueUrl=request_queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=5)

        if 'Messages' in msgs:
            msg = msgs['Messages'][0]
            image_name = msg['Body']
            print(f"Processing request for image: {image_name}")

            
            process_image(image_name)

            
            sqs.delete_message(QueueUrl=request_queue_url, ReceiptHandle=msg['ReceiptHandle'])
            print(f"Deleted message for {image_name} from request queue.")

if __name__ == "__main__":
    print("Starting backend")
    main()
