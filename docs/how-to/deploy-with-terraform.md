---
myst:
  html_meta:
    "description lang=en": "How to deploy the HAProxy charm using Terraform."
---


(how-to-deploy-with-terraform)=

# How to add HAProxy charm to existing Terraform project

Since the HAProxy charm provides ingress to another charm, you should already have a Terraform project with the definition of the charms you want to integrate with HAProxy.

The steps of integrating the HAProxy charm to an existing charm in Terraform are:

1. Add the HAProxy charm module to your Terraform project.
2. Add the relation between the HAProxy charm and the other charm.

## Add the HAProxy charm module to your Terraform project

The minimal Terraform module would look like this:

```hcl
module "haproxy_module" {
  source     = "git::https://github.com/canonical/haproxy-operator//terraform/product?ref=main"
  model_uuid = "juju-model-uuid"

  protected_hostnames_configuration = [{hostname = "example.com"}]
}
```

Replace the `"juju-model-uuid"` with the UUID of the model you want to deploy to. 

Generally it is recommended to change the `ref=main` to a specific release tag of the HAProxy charm, so the Terraform module will be fixed to a version.

The {ref}`Terraform module reference <reference_terraform>` has more details about the module and its parameters which can be added to the module definition to control the deployment.

## Add the relation between the HAProxy charm and the other charm

The existing charm need to be integrated to the HAProxy charm with the `juju_integration` resource, like the following example:

```hcl
resource "juju_integration" "haproxy_route" {
  model = var.model_uuid

  application {
    name     = module.haproxy_module.haproxy_app_name
    endpoint = "haproxy-route"
  }

  application {
    name     = "other-charm-name"
  }
}
```

## Apply the changes

The Terraform plan should be ready for deployment. Run `terraform apply` to apply the changes, deploy the HAProxy charm, and integrate it to the other charm.
