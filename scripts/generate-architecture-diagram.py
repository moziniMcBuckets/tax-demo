#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Generate detailed architecture diagram for Tax Document Collection Agent.

This script creates a comprehensive architecture diagram showing all components,
data flows, and integrations in the tax demo application.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.storage import S3
from diagrams.aws.security import Cognito, SecretsManager
from diagrams.aws.integration import SNS, SQS
from diagrams.aws.engagement import SES
from diagrams.aws.management import Cloudwatch, ParameterStore
from diagrams.aws.network import APIGateway
from diagrams.aws.ml import Bedrock
from diagrams.onprem.client import User
from diagrams.generic.blank import Blank

def generate_diagram():
    """Generate the tax demo architecture diagram."""
    
    with Diagram(
        "Tax Document Collection Agent - Detailed Architecture",
        filename="docs/architecture-diagram/tax-demo-detailed-architecture",
        direction="TB",
        show=False,
        graph_attr={
            "fontsize": "14",
            "bgcolor": "white",
            "pad": "0.5",
        }
    ):
        # Users
        with Cluster("Users"):
            accountant = User("Accountant")
            client = User("Client")
        
        # Frontend Layer
        with Cluster("Frontend - AWS Amplify Hosting"):
            with Cluster("React Application (Next.js 16)"):
                chat = Blank("Chat Interface")
                dashboard = Blank("Dashboard View")
                upload_portal = Blank("Upload Portal")
        
        # Authentication
        with Cluster("Authentication & Authorization"):
            cognito = Cognito("Cognito User Pool\n(User Auth)")
            cognito_machine = Cognito("Machine Client\n(OAuth2 M2M)")
        
        # AgentCore Layer
        with Cluster("Amazon Bedrock AgentCore"):
            with Cluster("AgentCore Runtime (Docker/ARM64)"):
                agent = Bedrock("Strands Agent\nClaude 3.5 Haiku")
                memory = Bedrock("AgentCore Memory\n(120 days retention)")
            
            gateway = APIGateway("AgentCore Gateway\n(MCP Protocol)\n6 Tools")
        
        # Lambda Tools Layer
        with Cluster("Lambda Functions (ARM64, Python 3.13)"):
            with Cluster("Gateway Tools"):
                doc_checker = Lambda("Document\nChecker")
                email_sender = Lambda("Email\nSender")
                status_tracker = Lambda("Status\nTracker")
            
            with Cluster("Management Tools"):
                escalation_mgr = Lambda("Escalation\nManager")
                requirement_mgr = Lambda("Requirement\nManager")
                upload_mgr = Lambda("Upload\nManager")
            
            doc_processor = Lambda("Document\nProcessor\n(S3 Event)")
        
        # Data Layer
        with Cluster("Data Storage"):
            with Cluster("DynamoDB Tables (Provisioned 1 RCU/WCU)"):
                clients_table = Dynamodb("Clients\n(GSI: accountant)")
                docs_table = Dynamodb("Documents")
                followups_table = Dynamodb("Followups")
                settings_table = Dynamodb("Settings")
            
            feedback_table = Dynamodb("Feedback\n(On-Demand)")
            s3_bucket = S3("Document Storage\n(Intelligent Tiering)\n7-year retention")
        
        # External Services
        with Cluster("AWS Services"):
            ses = SES("Amazon SES\n(Email Delivery)")
            sns = SNS("SNS\n(Notifications)")
            cloudwatch = Cloudwatch("CloudWatch\n(Logs & Metrics)")
            ssm = ParameterStore("SSM\nParameter Store")
            secrets = SecretsManager("Secrets Manager")
        
        # ===== USER FLOWS =====
        
        # Accountant login flow
        accountant >> Edge(label="1. Login", color="blue") >> cognito
        cognito >> Edge(label="2. JWT", color="blue") >> chat
        
        # Client upload flow
        client >> Edge(label="1. Access", color="green") >> upload_portal
        
        # ===== FRONTEND TO BACKEND =====
        
        # Chat to Agent
        chat >> Edge(label="HTTPS + JWT", color="darkblue") >> agent
        dashboard >> Edge(label="HTTPS + JWT", color="darkblue") >> agent
        
        # Agent Memory Integration
        agent >> Edge(label="Store/Retrieve\nConversations", color="purple") >> memory
        
        # ===== AGENT TO GATEWAY =====
        
        # Machine-to-machine auth for Gateway
        cognito_machine >> Edge(label="OAuth2\nClient Credentials", color="orange") >> gateway
        
        # Agent calls Gateway tools via MCP
        agent >> Edge(label="MCP Protocol\nTool Calls", color="red", style="bold") >> gateway
        
        # ===== GATEWAY TO LAMBDA TOOLS =====
        
        gateway >> Edge(label="Invoke", color="red") >> doc_checker
        gateway >> Edge(label="Invoke", color="red") >> email_sender
        gateway >> Edge(label="Invoke", color="red") >> status_tracker
        gateway >> Edge(label="Invoke", color="red") >> escalation_mgr
        gateway >> Edge(label="Invoke", color="red") >> requirement_mgr
        gateway >> Edge(label="Invoke", color="red") >> upload_mgr
        
        # ===== LAMBDA TO DYNAMODB =====
        
        # Document Checker
        doc_checker >> Edge(label="Read", color="brown") >> clients_table
        doc_checker >> Edge(label="Read", color="brown") >> docs_table
        
        # Email Sender
        email_sender >> Edge(label="Read", color="brown") >> clients_table
        email_sender >> Edge(label="Write", color="brown") >> followups_table
        email_sender >> Edge(label="Read Templates", color="brown") >> settings_table
        
        # Status Tracker
        status_tracker >> Edge(label="Query GSI", color="brown") >> clients_table
        
        # Escalation Manager
        escalation_mgr >> Edge(label="Update Status", color="brown") >> clients_table
        
        # Requirement Manager
        requirement_mgr >> Edge(label="CRUD", color="brown") >> docs_table
        
        # Upload Manager
        upload_mgr >> Edge(label="Read", color="brown") >> clients_table
        
        # ===== LAMBDA TO S3 =====
        
        doc_checker >> Edge(label="List Objects", color="darkgreen") >> s3_bucket
        upload_mgr >> Edge(label="Generate\nPresigned URL", color="darkgreen") >> s3_bucket
        doc_processor >> Edge(label="Process\nDocuments", color="darkgreen") >> s3_bucket
        
        # ===== S3 EVENT TRIGGER =====
        
        s3_bucket >> Edge(label="ObjectCreated\nEvent", color="darkgreen", style="dashed") >> doc_processor
        doc_processor >> Edge(label="Update\nStatus", color="brown") >> docs_table
        
        # ===== CLIENT UPLOAD FLOW =====
        
        upload_portal >> Edge(label="1. Request URL", color="green") >> upload_mgr
        upload_mgr >> Edge(label="2. Presigned URL", color="green") >> upload_portal
        upload_portal >> Edge(label="3. Direct Upload", color="green", style="bold") >> s3_bucket
        
        # ===== LAMBDA TO EXTERNAL SERVICES =====
        
        email_sender >> Edge(label="Send Email", color="purple") >> ses
        escalation_mgr >> Edge(label="Publish Alert", color="purple") >> sns
        
        # ===== LOGGING =====
        
        doc_checker >> Edge(label="Logs", color="gray", style="dotted") >> cloudwatch
        email_sender >> Edge(label="Logs", color="gray", style="dotted") >> cloudwatch
        status_tracker >> Edge(label="Logs", color="gray", style="dotted") >> cloudwatch
        escalation_mgr >> Edge(label="Logs", color="gray", style="dotted") >> cloudwatch
        requirement_mgr >> Edge(label="Logs", color="gray", style="dotted") >> cloudwatch
        upload_mgr >> Edge(label="Logs", color="gray", style="dotted") >> cloudwatch
        doc_processor >> Edge(label="Logs", color="gray", style="dotted") >> cloudwatch
        agent >> Edge(label="Logs", color="gray", style="dotted") >> cloudwatch
        
        # ===== CONFIGURATION =====
        
        gateway >> Edge(label="Read Config", color="black", style="dashed") >> ssm
        agent >> Edge(label="Read Config", color="black", style="dashed") >> ssm
        email_sender >> Edge(label="Read Secrets", color="black", style="dashed") >> secrets
    
    print("✅ Architecture diagram generated successfully!")
    print("📁 Location: docs/architecture-diagram/tax-demo-detailed-architecture.png")

if __name__ == "__main__":
    generate_diagram()
