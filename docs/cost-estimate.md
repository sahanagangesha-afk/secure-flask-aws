# Cost estimate (approximate, ap-south-1 / Mumbai, always-on, on-demand)

Prices change - confirm with the [AWS Pricing Calculator](https://calculator.aws/). Figures below are rough monthly ballparks in USD.

| Resource | Config | ~Monthly |
|---|---|---|
| EC2 | 1 x t3.micro (ASG min 1) | 8-10 |
| Application Load Balancer | 1 ALB, light traffic | 18-22 |
| RDS MySQL | db.t3.micro, 20 GB gp2, single-AZ | 15-20 |
| EBS | 12 GB gp3 per instance | 1-2 |
| S3 | a few GB of backups | <1 |
| CloudWatch | logs + agent metrics + 4 alarms | 2-5 |
| NAT Gateway | **not used** (instances sit in public subnets) | 0 (saves ~30+) |
| **Total** | | **~45-60** |

Notes
- Free-tier eligibility varies by account age/region. The ALB and RDS are the biggest cost items.
- Scale-out during the stress test adds up to 2 more t3.micro instances only while load lasts.
- The AWS Budget alarm (default $20, change `monthly_budget_usd`) emails you at 50% / 80% actual and 100% forecast.
- **Tear down when finished: `terraform destroy`** - leaving the ALB + RDS running is the usual surprise bill.
- Cheaper variants: drop the ALB/ASG and run one EC2 + RDS (~$25-30), or run SQLite on EC2 only.
