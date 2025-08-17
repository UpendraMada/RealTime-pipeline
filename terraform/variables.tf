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
  default = 1500.0
}

variable "alarm_email" {
  type    = string
  default = "upendra2813@gmail.com"
}

variable "txn_email" {
  type    = string
  default = "upendra2813@gmail.com"
}
