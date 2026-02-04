# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# RainCity Operations Squad - Docker Image
# Multi-agent squad with Swarm orchestration

FROM public.ecr.aws/docker/library/python:3.13-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY operations_squad.py .

# Copy gateway utilities
COPY ../../gateway/utils/ ./gateway/utils/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-west-2

# Run the agent
CMD ["python", "operations_squad.py"]
