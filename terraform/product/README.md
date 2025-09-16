<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | >= 0.19.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | >= 0.19.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_haproxy"></a> [haproxy](#module\_haproxy) | ../charm | n/a |

## Resources

| Name | Type |
|------|------|
| [juju_application.grafana_agent](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |
| [juju_integration.grafana_agent](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_model.haproxy](https://registry.terraform.io/providers/juju/juju/latest/docs/data-sources/model) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_grafana_agent"></a> [grafana\_agent](#input\_grafana\_agent) | n/a | <pre>object({<br/>    channel  = optional(string, "latest/stable")<br/>    config   = optional(map(string), {})<br/>    revision = optional(number, null)<br/>  })</pre> | `{}` | no |
| <a name="input_hacluster"></a> [hacluster](#input\_hacluster) | n/a | <pre>object({<br/>    channel  = optional(string, "2.4/edge")<br/>    config   = optional(map(string), {})<br/>    revision = optional(number, null)<br/>  })</pre> | `{}` | no |
| <a name="input_haproxy"></a> [haproxy](#input\_haproxy) | n/a | <pre>object({<br/>    app_name    = optional(string, "haproxy")<br/>    channel     = optional(string, "2.8/edge")<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, "arch=amd64")<br/>    revision    = optional(number)<br/>    base        = optional(string, "ubuntu@24.04")<br/>    units       = optional(number, 1)<br/>  })</pre> | `{}` | no |
| <a name="input_model"></a> [model](#input\_model) | Reference to the Juju model to deploy application to. | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_grafana_agent"></a> [grafana\_agent](#output\_grafana\_agent) | Name of the deployed grafana-agent application. |
| <a name="output_provides"></a> [provides](#output\_provides) | n/a |
| <a name="output_requires"></a> [requires](#output\_requires) | n/a |
<!-- END_TF_DOCS -->