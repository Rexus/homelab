package Structure {
    item def <'PAYLOAD'> Transfer;
    port def <'IF-transfer'> TransferPort { inout item payload : Transfer; }
    part def <'DEF-source'> ApprovedSource {
        doc /* Abstract role of an external repository service; an allowlist is a separate policy asset. */
        port access : TransferPort;
    }
    part def <'DEF-client'> UpdateClient {
        port access : TransferPort;
        doc /* Pull through the accepted route and verify publisher metadata/signatures locally. */
    }
    part def <'DEF-listener'> SharedListener {
        port inbound : TransferPort;
        port dispatch : TransferPort;
    }
    part def <'DEF-member'> ProxyMember {
        doc /* A software/virtual-resource member. Its guest storage does not identify a physical drive or host. */
        part <'DEF-member-proxy'> proxy : PolicyProxy;
        part <'DEF-member-cache'> storage : DisposableCache;
        dependency <'DEP-storage'> 'Uses local rebuildable storage' from proxy to storage;
    }

}
