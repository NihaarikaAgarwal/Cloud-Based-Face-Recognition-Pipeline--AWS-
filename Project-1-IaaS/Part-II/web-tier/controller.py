import boto3
import time

REGION = "us-east-1"
ASU_ID = ""
INSTANCE_TYPE = "t2.micro"
MAX_INSTANCES = 15
SQS_REQUEST_QUEUE = f"{ASU_ID}-req-queue"
APP_INSTANCE_TAG = "app-tier-instance"

sqs = boto3.client('sqs', region_name=REGION)
ec2 = boto3.client('ec2', region_name=REGION)

def get_queue_stats():
    
    queue_url = sqs.get_queue_url(QueueName=SQS_REQUEST_QUEUE)['QueueUrl']
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
    )
    visible = int(attrs['Attributes']['ApproximateNumberOfMessages'])
    not_visible = int(attrs['Attributes']['ApproximateNumberOfMessagesNotVisible'])
    return visible, not_visible

def get_all_app_instances():
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': [f"{APP_INSTANCE_TAG}-*"]},
            {'Name': 'instance-state-name', 'Values': ['running', 'stopped', 'pending', 'stopping']}
        ]
    )
    instances = []
    for res in response['Reservations']:
        for inst in res['Instances']:
            instance_id = inst['InstanceId']
            state = inst['State']['Name']
            name = next((tag['Value'] for tag in inst.get('Tags', []) if tag['Key'] == 'Name'), None)
            instances.append({'id': instance_id, 'name': name, 'state': state})
    return instances

def start_instances(count):
    instances = get_all_app_instances()
    stopped_instances = [inst for inst in instances if inst['state'] == 'stopped']

    instances_to_start = stopped_instances[:count]
    instance_ids = [inst['id'] for inst in instances_to_start]

    if instance_ids:
        print(f"Starting instances: {[inst['name'] for inst in instances_to_start]}")
        ec2.start_instances(InstanceIds=instance_ids)
        print("Waiting 30 seconds")
        time.sleep(30)
    else:
        print("No stopped instances available to start.")

def stop_instances():
    instances = get_all_app_instances()
    running_instances = [inst for inst in instances if inst['state'] == 'running']

    instance_ids = [inst['id'] for inst in running_instances]
    if instance_ids:
        print(f"Stopping instances: {[inst['name'] for inst in running_instances]}")
        ec2.stop_instances(InstanceIds=instance_ids)

def autoscale():
    while True:
        visible, not_visible = get_queue_stats()
        total_pending = visible + not_visible

        instances = get_all_app_instances()
        active_instances = [inst for inst in instances if inst['state'] in ['running', 'pending']]

        print(f"Visible: {visible}, In-flight: {not_visible} | Active instances: {len(active_instances)}")

        if total_pending > 0 and len(active_instances) < MAX_INSTANCES:
            needed = min(total_pending - len(active_instances), MAX_INSTANCES - len(active_instances))
            if needed > 0:
                start_instances(needed)

        elif visible == 0 and not_visible == 0 and active_instances:
            print("All messages processed")
            stop_instances()

        time.sleep(10)

if __name__ == "__main__":
    print("Autoscaler started")
    autoscale()
