"""
Helper script to generate validated CloudFront distribution configuration
and S3 Origin Access Control (OAC) bucket policy JSON for ClearSky Intelligence.
"""
import sys
import json
import argparse


def generate_distribution_config(caller_ref: str, bucket: str, region: str, oac_id: str, comment: str) -> dict:
    s3_origin_id = f"S3-{bucket}"
    s3_domain = f"{bucket}.s3.{region}.amazonaws.com"
    return {
        "CallerReference": caller_ref,
        "Aliases": {"Quantity": 0},
        "DefaultRootObject": "index.html",
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": s3_origin_id,
                    "DomainName": s3_domain,
                    "OriginPath": "",
                    "CustomHeaders": {"Quantity": 0},
                    "S3OriginConfig": {"OriginAccessIdentity": ""},
                    "OriginAccessControlId": oac_id,
                    "ConnectionAttempts": 3,
                    "ConnectionTimeout": 10,
                    "OriginShield": {"Enabled": False}
                }
            ]
        },
        "OriginGroups": {"Quantity": 0},
        "DefaultCacheBehavior": {
            "TargetOriginId": s3_origin_id,
            "TrustedSigners": {"Enabled": False, "Quantity": 0},
            "TrustedKeyGroups": {"Enabled": False, "Quantity": 0},
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": {
                "Quantity": 2,
                "Items": ["GET", "HEAD"],
                "CachedMethods": {
                    "Quantity": 2,
                    "Items": ["GET", "HEAD"]
                }
            },
            "SmoothStreaming": False,
            "Compress": True,
            "LambdaFunctionAssociations": {"Quantity": 0},
            "FunctionAssociations": {"Quantity": 0},
            "FieldLevelEncryptionId": "",
            "ForwardedValues": {
                "QueryString": False,
                "Cookies": {"Forward": "none"},
                "Headers": {"Quantity": 0},
                "QueryStringCacheKeys": {"Quantity": 0}
            },
            "MinTTL": 0,
            "DefaultTTL": 86400,
            "MaxTTL": 31536000
        },
        "CacheBehaviors": {"Quantity": 0},
        "CustomErrorResponses": {
            "Quantity": 2,
            "Items": [
                {
                    "ErrorCode": 403,
                    "ResponsePagePath": "/index.html",
                    "ResponseCode": "200",
                    "ErrorCachingMinTTL": 0
                },
                {
                    "ErrorCode": 404,
                    "ResponsePagePath": "/index.html",
                    "ResponseCode": "200",
                    "ErrorCachingMinTTL": 0
                }
            ]
        },
        "Comment": comment,
        "Logging": {
            "Enabled": False,
            "IncludeCookies": False,
            "Bucket": "",
            "Prefix": ""
        },
        "PriceClass": "PriceClass_100",
        "Enabled": True,
        "ViewerCertificate": {
            "CloudFrontDefaultCertificate": True,
            "MinimumProtocolVersion": "TLSv1.2_2021",
            "CertificateSource": "cloudfront"
        },
        "Restrictions": {
            "GeoRestriction": {
                "RestrictionType": "none",
                "Quantity": 0
            }
        },
        "HttpVersion": "http2"
    }


def generate_oac_bucket_policy(bucket: str, account_id: str, dist_id: str) -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCloudFrontOACReadOnly",
                "Effect": "Allow",
                "Principal": {
                    "Service": "cloudfront.amazonaws.com"
                },
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/*",
                "Condition": {
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{account_id}:distribution/{dist_id}"
                    }
                }
            }
        ]
    }


def main():
    parser = argparse.ArgumentParser(description="Generate CloudFront or S3 Policy configuration")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dist_parser = subparsers.add_parser("distribution")
    dist_parser.add_argument("--caller-ref", required=True)
    dist_parser.add_argument("--bucket", required=True)
    dist_parser.add_argument("--region", default="us-east-1")
    dist_parser.add_argument("--oac-id", required=True)
    dist_parser.add_argument("--comment", required=True)
    dist_parser.add_argument("--output", required=True)

    policy_parser = subparsers.add_parser("policy")
    policy_parser.add_argument("--bucket", required=True)
    policy_parser.add_argument("--account-id", required=True)
    policy_parser.add_argument("--dist-id", required=True)
    policy_parser.add_argument("--output", required=True)

    args = parser.parse_args()

    if args.command == "distribution":
        cfg = generate_distribution_config(
            caller_ref=args.caller_ref,
            bucket=args.bucket,
            region=args.region,
            oac_id=args.oac_id,
            comment=args.comment
        )
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print(f"Generated CloudFront distribution config at {args.output}")

    elif args.command == "policy":
        pol = generate_oac_bucket_policy(
            bucket=args.bucket,
            account_id=args.account_id,
            dist_id=args.dist_id
        )
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(pol, f, indent=2)
        print(f"Generated S3 OAC policy at {args.output}")


if __name__ == "__main__":
    main()
