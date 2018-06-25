# Steps To Create Rpm Builder VM

* Create rpm builder VM using [Jenkins Job](https://jenkins.awsxpc.comcast.net/job/create_instances_modulewise/) (Args: project=xpc, rpmbuilder=1, region=your choice preferred ch2h or hoc and color=devops)
* Update the VM Ip address (from above output) in the ansible path [inventory/rpmbuilder/hosts]
* Run the below command after cloning the ansible repo, make sure in the below command you replcae the ipaddress with above updated ipaddress, this way we will only apply the changes to the new VM also ensure your able to ssh in to it.

```ansible-playbook -i inventory/rpmbuilder/hosts --limit <ipaddress> "site_admin_deploy=True" devops.yml```

* Create two volumes in openstack, one is 500 GB and another one is 300 GB and attach both volumes to the rpmbuilder VM

```
steps to configure LVMs:
     fdisk -l (to check disk name)
     pvcreate /dev/vdx (this should be 500 GB)
     pvcreate /dev/vdy ( this should be 300 GB)
     vgcreate lvm_group_www2 /dev/vdx
     vgcreate lvm_group_www /dev/vdy
     lvcreate -l 100%FREE -n lvm_volume_www2 lvm_group_www2
     lvcreate -l 100%FREE -n lvm_volume_www lvm_group_www
     mkfs.ext4 /dev/lvm_group_www2/lvm_volume_www2
     mkfs.ext4 /dev/lvm_group_www/lvm_volume_www
     mkdir /www2
     mkdir /www
     mount /dev/lvm_group_www2/lvm_volume_www2 /www2
     mount /dev/lvm_group_www/lvm_volume_www /www
     df -h
     blkid (get teh UUID to update the fstab)
     vi /etc/fstab
     ex:UUID=fad95bec-7604-4dbf-925e-a4ea150df713 /www2                   ext4    defaults        1 1
        UUID=122269da-47de-4a4c-930b-a7e774df2d71 /www                    ext4    defaults        1 1
     mkdir -p /www2/ATLAS/x86_64/6/global
     mkdir -p /www/html
     service nginx restart
