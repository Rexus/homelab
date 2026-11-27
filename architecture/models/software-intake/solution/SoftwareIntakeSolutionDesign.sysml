package SoftwareIntakeSolutionDesign {
    doc /* Selected solution: Squid performs admission, HTTP forwarding/reuse and source-TLS relay;
           keepalived supplies an active-owner listener. Each selected VM has independent rebuildable
           cache storage. Client verification and independent network enforcement retain their owners.
           Reference is generated from the tracked IaC examples, not discovered live state. Shared
           platform bindings connect virtual resources back to hardware without inventing site placement.
           Two VMs do not establish two physical failure domains. Revisit the selected arrangement for
           stronger policy separation, capacity or custody needs; preserve the logical contracts.
           The source-owned native requirements and verification cases define acceptance. A trace or
           successful rendering does not establish deployment, failover, Git/TLS or recovery behavior. */
    public import Reference::services;
}
