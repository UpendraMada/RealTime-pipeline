variable "project" {
  type    = string
  default = "rt-pipeline-user"
}
variable "region" {
  type    = string
  default = "us-east-1"
}

variable "alert_amount" {
  type    = number
  default = 500.0 # USD threshold for business alert
}

variable "alarm_email" {
  type    = string
  default = "upendra2813@gmail.com" # optional: email for CW alarms
}
