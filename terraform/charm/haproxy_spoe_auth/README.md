<!-- BEGIN_TF_DOCS -->
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
| [juju_application.haproxy_spoe_auth](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Application name of the deployed haproxy-spoe-auth charm. | `string` | `"haproxy-spoe-auth"` | no |
| <a name="input_base"></a> [base](#input\_base) | Base of the haproxy-spoe-auth charm. | `string` | `"ubuntu@24.04"` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | Revision of the haproxy-spoe-auth charm. | `string` | `"2.8/edge"` | no |
| <a name="input_config"></a> [config](#input\_config) | haproxy-spoe-auth charm config. | `map(string)` | `{}` | no |
| <a name="input_constraints"></a> [constraints](#input\_constraints) | haproxy-spoe-auth constraints. | `string` | `"arch=amd64"` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | ID of the Juju model to deploy to. | `string` | n/a | yes |
| <a name="input_revision"></a> [revision](#input\_revision) | Revision of the haproxy-spoe-auth charm. | `number` | `null` | no |
| <a name="input_units"></a> [units](#input\_units) | Number of haproxy-spoe-auth units. | `number` | `1` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_app_name"></a> [app\_name](#output\_app\_name) | n/a |
| <a name="output_provides"></a> [provides](#output\_provides) | n/a |
| <a name="output_requires"></a> [requires](#output\_requires) | n/a |
<!-- END_TF_DOCS -->