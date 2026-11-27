package Platform {
    doc /* Shared platform boundary contracts. These are documented provider roles, not a complete
           hosting/network model or discovered physical inventory. Existing platform guides own detail. */
    port def <'P-IF-physical'> PhysicalAttachment;
    part def <'P-DEF-virtualization'> VirtualizationProvider;
    part def <'P-DEF-storage'> GuestStorageProvider;
    part def <'P-DEF-network'> GuestNetworkProvider;
    part def <'P-DEF-logical-network'> LogicalTransport;
    part def <'P-DEF-equipment'> Equipment { port attachment : PhysicalAttachment; }
    part <'P-context'> platform {
        part <'P-virtualization'> 'Proxmox virtualization' : VirtualizationProvider;
        part <'P-storage'> 'Local guest-disk service' : GuestStorageProvider;
        part <'P-network'> 'Guest network attachment' : GuestNetworkProvider;
        part <'P-fabric'> 'Logical fabric network' : LogicalTransport;
        part <'P-storage-network'> 'Logical storage network' : LogicalTransport {
            doc /* Optional dual-fabric reference. Not required by the selected local cache disks. */
        }
        part <'P-servers'> 'Physical servers' : Equipment;
        part <'P-drives'> 'Physical storage devices' : Equipment;
        part <'P-switches'> 'Physical switches and NICs' : Equipment;
        dependency <'P-hosting'> 'Runs on' from 'Proxmox virtualization' to 'Physical servers';
        dependency <'P-storage-provider'> from 'Local guest-disk service' to 'Proxmox virtualization';
        dependency <'P-network-provider'> from 'Guest network attachment' to 'Proxmox virtualization';
        dependency <'P-disk-backing'> 'Backed by' from 'Local guest-disk service' to 'Physical storage devices';
        dependency <'P-fabric-use'> 'Uses logical transport' from 'Guest network attachment' to 'Logical fabric network';
        dependency <'P-fabric-backing'> 'Realized over' from 'Logical fabric network' to 'Physical switches and NICs';
        dependency <'P-storage-network-backing'> 'Realized over when selected' from 'Logical storage network' to 'Physical switches and NICs';
        connection <'P-cabling'> 'Physical attachment' connect 'Physical servers'.attachment to 'Physical switches and NICs'.attachment;
    }
}
