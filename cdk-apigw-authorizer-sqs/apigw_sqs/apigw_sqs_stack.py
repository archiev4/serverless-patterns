from aws_cdk import (
    core as core,
    aws_sqs as sqs,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_lambda as lambdafun
)

class ApigwSqsStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

# Define Parameters that customers can use in properties of constructs.
        storage_sqs_queue_name = core.CfnParameter(self, "storagequeue", type="String",
            default='storagequeue-noauth',
            description="Enter the name of the Amazon SQS queue where events will be stored."
        )
        aws_region_name = core.CfnParameter(self, "awsregion", type="String",
            default='us-east-1',
            description="Enter the AWS region name where the resources need to be deployed."
        )
        need_an_authorizer = core.CfnParameter(self, "authorizerneeded", type="String",
                allowed_values= ["No"],
                default="No",
                description= "This stack does not take create an Authorizer.",
    
        )       
        


# Create a SQS queue for storing message that APIGateway will receive.
        sqs_queue = sqs.Queue(self, 
                    'storagesqs',          
                    queue_name = storage_sqs_queue_name.value_as_string,
                    encryption = sqs.QueueEncryption.KMS_MANAGED
        )
        
# Create an inline Policy document that grants permission to access SQS queue
        sqs_inline_policy = iam.Policy(self, "sqs-policy-for-apigw",
            statements=[iam.PolicyStatement(
                actions=["sqs:SendMessage"],
                resources=[sqs_queue.queue_arn]
            )]
        )
# Create an IAM  apigateway execution role.
        apigw_role = iam.Role(self, "apigw_role",
                    assumed_by=iam.CompositePrincipal(
                            iam.ServicePrincipal("apigateway.amazonaws.com"), 
                            iam.ServicePrincipal("lambda.amazonaws.com")
                    ),       
                    description="This is the role for apigateway to access SQS queue."
        )
# Attach policy to the role.       
        apigw_role.attach_inline_policy(sqs_inline_policy)

# Create new Integration Options that can for adding request paramaters and templates.
        integration_options = apigateway.IntegrationOptions(
                    credentials_role = apigw_role,
                    request_parameters={
                        'integration.request.header.Content-Type' : "'application/x-www-form-urlencoded'"
                    },
                    passthrough_behavior=apigateway.PassthroughBehavior.NEVER,
                    request_templates={
                        "application/json": "Action=SendMessage&MessageBody=$input.body"
                    },
                    integration_responses=[apigateway.IntegrationResponse(status_code="200")],
        )

# Create new apigateway rest api.      
        apigw = apigateway.RestApi(self, 'sqsapi-noauth',
                description ='This api will insert data into SQS ' + sqs_queue.queue_name,
                endpoint_types =[apigateway.EndpointType.REGIONAL]
        )
        
# Create a apigateway resource method with authorizer needed   

        apigw_method = apigw.root.add_resource('sqs').add_method('POST',
            apigateway.AwsIntegration(
                region = aws_region_name.value_as_string,
                service = 'sqs',
                integration_http_method = 'POST',
                path = sqs_queue.queue_name, 
                options = integration_options
            ),
            method_responses=[apigateway.MethodResponse(status_code="200")],

        )
