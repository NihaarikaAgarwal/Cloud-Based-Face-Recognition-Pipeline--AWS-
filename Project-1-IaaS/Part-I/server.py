import os
import csv
import boto3
from flask import Flask, request
from botocore.exceptions import ClientError


ASU_ID = ""  
REGION = "us-east-1"

S3_BUCKET = f"{ASU_ID}-in-bucket"
SIMPLEDB_DOMAIN = f"{ASU_ID}-simpleDB"

s3_client = boto3.client("s3", region_name=REGION)
sdb_client = boto3.client("sdb", region_name=REGION)

app = Flask(__name__)

def creating_simpledb():
    try:
        response = sdb_client.list_domains()
        if SIMPLEDB_DOMAIN in response.get('DomainNames', []):
            print(f"SimpleDB domain {SIMPLEDB_DOMAIN} already exists.")
        else:
            sdb_client.create_domain(DomainName=SIMPLEDB_DOMAIN)
            print(f"Created SimpleDB domain: {SIMPLEDB_DOMAIN}")
    except ClientError as e:
        print(f"Error in creating SimpleDB domain: {e}")

def populate_simpledb(csv_file_path):
    with open(csv_file_path, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            image_id = row['Image']  
            result = row['Results']  
            attributes = {key: value for key, value in row.items()}
            #print(f"Populating SimpleDB: {image_id} -> {result}")
            try:
                sdb_client.put_attributes(
                    DomainName=SIMPLEDB_DOMAIN,
                    ItemName= image_id,
                    Attributes=[{'Name': 'Results', 'Value': result, 'Replace': True},
                    ]
                )
            except Exception as e:
                print(f"Error in reading CSV file: {e}")

def query_simpledb(query_image):
    #print("Enter query_simpledb")
    print(f"image name: '{query_image}'")
    try:
        response = sdb_client.get_attributes(DomainName=SIMPLEDB_DOMAIN, ItemName=query_image)
        #print(f"Response from SimpleDB {query_image}: {response}")
        if 'Attributes' in response:
            for attr in response['Attributes']:
                print(f"Attribute: {attr['Name']} = {attr['Value']}")
            return response['Attributes'][0]['Value'] 
        else:
            return "Unknown"
    except Exception as e:
        print(f"Error querying SimpleDB for {query_image}: {e}")
        return "Error"

@app.route("/", methods=["POST"])
def handling_HTTP_request():

    if "inputFile" not in request.files:
        return "Missing 'inputFile' in request", 400
    file = request.files["inputFile"]
    file_name = file.filename
    if not file_name:
        return "Invalid file name", 400

    try:
        s3_client.upload_fileobj(file, S3_BUCKET, file_name)
        print(f"Uploaded {file_name} to S3 bucket {S3_BUCKET}")
    except Exception as e:
        return f"Error uploading to S3: {e}", 500

    root_file_name = os.path.splitext(file_name)[0]
    query_answer = query_simpledb(root_file_name)

    return f"{file_name}:{query_answer}", 200
    
if __name__ == "__main__":
    creating_simpledb()
    csv_file_path = "classification_dataset.csv"
    populate_simpledb(csv_file_path)
    print("Starting Flask server on port 8000")
    app.run(host="0.0.0.0", port=8000, threaded = True)
