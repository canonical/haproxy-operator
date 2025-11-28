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
| [juju_application.hacluster](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |
| [juju_application.haproxy](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |
| [juju_application.keepalived](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |
| [juju_integration.ha](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.keepalived](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Application name of the deployed haproxy charm. | `string` | `"haproxy"` | no |
| <a name="input_base"></a> [base](#input\_base) | Base of the haproxy charm. | `string` | `"ubuntu@24.04"` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | Revision of the haproxy charm. | `string` | `"2.8/edge"` | no |
| <a name="input_config"></a> [config](#input\_config) | Haproxy charm config. | `map(string)` | `{}` | no |
| <a name="input_constraints"></a> [constraints](#input\_constraints) | Haproxy constraints. | `string` | `"arch=amd64"` | no |
| <a name="input_hacluster_app_name"></a> [hacluster\_app\_name](#input\_hacluster\_app\_name) | Application name of the hacluster charm. | `string` | `"hacluster"` | no |
| <a name="input_hacluster_charm_channel"></a> [hacluster\_charm\_channel](#input\_hacluster\_charm\_channel) | Channel of the hacluster charm. | `string` | `"2.4/edge"` | no |
| <a name="input_hacluster_charm_revision"></a> [hacluster\_charm\_revision](#input\_hacluster\_charm\_revision) | Revision of the hacluster charm. | `number` | `null` | no |
| <a name="input_hacluster_config"></a> [hacluster\_config](#input\_hacluster\_config) | Hacluster charm config. | `map(string)` | `{}` | no |
| <a name="input_keepalived_app_name"></a> [keepalived\_app\_name](#input\_keepalived\_app\_name) | Application name of the keepalived charm. | `string` | `"keepalived"` | no |
| <a name="input_keepalived_charm_channel"></a> [keepalived\_charm\_channel](#input\_keepalived\_charm\_channel) | Channel of the keepalived charm. | `string` | `"latest/edge"` | no |
| <a name="input_keepalived_charm_revision"></a> [keepalived\_charm\_revision](#input\_keepalived\_charm\_revision) | Revision of the keepalived charm. | `number` | `null` | no |
| <a name="input_keepalived_config"></a> [keepalived\_config](#input\_keepalived\_config) | Keepalived charm config. | `map(string)` | `{}` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | ID of the Juju model to deploy to. | `string` | n/a | yes |
| <a name="input_revision"></a> [revision](#input\_revision) | Revision of the haproxy charm. | `number` | `null` | no |
| <a name="input_units"></a> [units](#input\_units) | Number of haproxy units. If hacluster is enabled, it is recommended to use a value > 3 to ensure a quorum. | `number` | `1` | no |
| <a name="input_use_hacluster"></a> [use\_hacluster](#input\_use\_hacluster) | Whether to use hacluster for active/passive. | `bool` | `false` | no |
| <a name="input_use_keepalived"></a> [use\_keepalived](#input\_use\_keepalived) | Whether to use keepalived for active/passive. | `bool` | `false` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_app_name"></a> [app\_name](#output\_app\_name) | n/a |
| <a name="output_provides"></a> [provides](#output\_provides) | n/a |
| <a name="output_requires"></a> [requires](#output\_requires) | n/a |
<!-- END_TF_DOCS -->