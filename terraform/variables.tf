variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "project_name" {
  type    = string
  default = "flask-fraud"
}

variable "my_ip_cidr" {
  description = "Your public IP in CIDR form for SSH, e.g. 203.0.113.10/32"
  type        = string
  validation {
    condition     = can(cidrhost(var.my_ip_cidr, 0)) && var.my_ip_cidr != "0.0.0.0/0"
    error_message = "Provide your own IP as x.x.x.x/32 (0.0.0.0/0 is not allowed)."
  }
}

variable "alert_email" {
  description = "Email for CloudWatch alarms and budget alerts"
  type        = string
}

variable "repo_url" {
  description = "Public HTTPS URL of your GitHub repo (cloned by the instances)"
  type        = string
}

variable "key_name" {
  description = "Existing EC2 key pair name for SSH (optional)"
  type        = string
  default     = null
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "asg_min" {
  type    = number
  default = 1
}

variable "asg_max" {
  type    = number
  default = 3
}

variable "monthly_budget_usd" {
  type    = number
  default = 20
}

variable "certificate_arn" {
  description = "Optional ACM certificate ARN. If set, ALB serves HTTPS on 443 and redirects HTTP."
  type        = string
  default     = ""
}

variable "enable_stress_endpoint" {
  description = "Enable /stress endpoint for the Auto Scaling demo. Turn off afterwards."
  type        = bool
  default     = false
}
