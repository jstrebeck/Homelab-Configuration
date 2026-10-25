#Patch
talosctl patch mc -p @talos-patch.yaml -n 192.168.2.104,192.168.2.105,192.168.2.106,192.168.2.107

## Removing an image

Deletes are enabled (`REGISTRY_STORAGE_DELETE_ENABLED`). To remove a
repository entirely, delete its directory and garbage-collect; dry-run first
and check that only that image's blobs are listed. Don't push while GC runs.

```
kubectl -n registry exec deploy/registry -- rm -rf /var/lib/registry/docker/registry/v2/repositories/<name>
kubectl -n registry exec deploy/registry -- registry garbage-collect --dry-run /etc/distribution/config.yml
kubectl -n registry exec deploy/registry -- registry garbage-collect /etc/distribution/config.yml
```
