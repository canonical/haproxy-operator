<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.6 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | >= 1.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | >= 1.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [juju_application.haproxy](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Application name of the deployed haproxy charm. | `string` | `"haproxy"` | no |
| <a name="input_base"></a> [base](#input\_base) | Base of the haproxy charm. | `string` | `"ubuntu@26.04"` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | Channel of the haproxy charm. | `string` | `"3.2/edge"` | no |
| <a name="input_config"></a> [config](#input\_config) | Haproxy charm config. | `map(string)` | `{}` | no |
| <a name="input_constraints"></a> [constraints](#input\_constraints) | Haproxy constraints. | `string` | `"arch=amd64"` | no |
| <a name="input_machines"></a> [machines](#input\_machines) | Machines to deploy haproxy units to. Mutually exclusive with units. | `set(string)` | `null` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | ID of the Juju model to deploy to. | `string` | n/a | yes |
| <a name="input_revision"></a> [revision](#input\_revision) | Revision of the haproxy charm. | `number` | `null` | no |
| <a name="input_units"></a> [units](#input\_units) | Number of haproxy units. | `number` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_app_name"></a> [app\_name](#output\_app\_name) | n/a |
| <a name="output_application"></a> [application](#output\_application) | The deployed haproxy application object. |
| <a name="output_provides"></a> [provides](#output\_provides) | Map of provided endpoints. |
| <a name="output_requires"></a> [requires](#output\_requires) | Map of required endpoints. |
<!-- END_TF_DOCS -->