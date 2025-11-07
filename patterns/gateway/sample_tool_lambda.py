import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Sample tool Lambda function for GASP Gateway
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Parse the MCP request
        body = json.loads(event.get('body', '{}'))
        tool_name = body.get('name')
        arguments = body.get('arguments', {})
        
        if tool_name == 'sample_tool':
            name = arguments.get('name', 'World')
            result = f"Hello, {name}! This is a sample tool from GASP."
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'content': [
                        {
                            'type': 'text',
                            'text': result
                        }
                    ]
                })
            }
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': f"Unknown tool: {tool_name}"
                })
            }
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': f"Internal server error: {str(e)}"
            })
        }
