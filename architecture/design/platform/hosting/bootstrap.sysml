package BootstrapDesign {
    doc /* A bounded reference to the existing bootstrap host, not a new managed VM or
           discovered hardware allocation. The bootstrap guide owns its deployment. */
    part def <'BOOT-DEF-operator'> BootstrapOperator { doc /* Person operating the bootstrap host. */ }
    part <'BOOT-operator'> operator : BootstrapOperator;
    part <'BOOT-host'> 'boot-1' : Structure::UpdateClient;
}
