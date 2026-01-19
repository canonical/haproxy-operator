## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.6 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | ~> 1.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | ~> 1.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [juju_application.haproxy_ddos_protection_configurator](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Application name of the deployed haproxy-ddos-protection-configurator charm. | `string` | `"haproxy-ddos-protection-configurator"` | no |
| <a name="input_base"></a> [base](#input\_base) | Base of the haproxy-ddos-protection-configurator charm. | `string` | `"ubuntu@24.04"` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | Channel of the haproxy-ddos-protection-configurator charm. | `string` | `"latest/edge"` | no |
| <a name="input_config"></a> [config](#input\_config) | haproxy-ddos-protection-configurator charm config. | `map(string)` | `{}` | no |
| <a name="input_constraints"></a> [constraints](#input\_constraints) | haproxy-ddos-protection-configurator constraints. | `string` | `"arch=amd64"` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | ID of the Juju model to deploy to. | `string` | n/a | yes |
| <a name="input_revision"></a> [revision](#input\_revision) | Revision of the haproxy-ddos-protection-configurator charm. | `number` | `null` | no |
| <a name="input_units"></a> [units](#input\_units) | Number of haproxy-ddos-protection-configurator units. | `number` | `1` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_app_name"></a> [app\_name](#output\_app\_name) | n/a |
| <a name="output_provides"></a> [provides](#output\_provides) | n/a |
| <a name="output_requires"></a> [requires](#output\_requires) | n/a |
