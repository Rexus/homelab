package BootstrapUseCases {
    use case def <'UC-clone'> 'Clone a Git repository over HTTPS' {
        subject <'UC-clone-host'> 'boot-1' : Structure::UpdateClient = BootstrapDesign::'boot-1';
        actor <'ACT-operator'> 'Operator' : BootstrapDesign::BootstrapOperator = BootstrapDesign::operator;
        actor <'ACT-intake'> 'Software intake' : SystemDesign::SoftwareIntakeSubsystem = SystemDesign::homelab.'Software intake';
        objective { doc /* Obtain a local checkout of an approved Git repository on boot-1
            through the accepted HTTPS route. A successful clone does not approve a revision. */ }
        doc Trigger /* The operator starts git clone with an approved HTTPS repository URL on boot-1. */
        doc Preconditions /* The accepted proxy is reachable, the Git source and CONNECT port are admitted,
            the current shell uses the proxy, and TLS verification remains enabled. */
        doc Scenario /* 1. The operator starts the clone on boot-1.
            2. Git on boot-1 requests access through software intake.
            3. Software intake admits the CONNECT request or returns a denial.
            4. Git validates the source TLS certificate and exchanges repository data through the tunnel.
            5. Git reports a local checkout or failure to the operator. */
        doc Limits /* Software intake remains a supporting boundary here. Its internal design and HTTPS
            exchanges have their own views. CONNECT payloads do not use the HTTP object cache.
            Denial, source failure or TLS failure stops the clone; signed commit/tag approval is a
            separate decision. This goal scenario is documented, not an executed Git verification case. */
    }
    dependency <'UC-clone-intake-behavior'> 'Uses the accepted HTTPS access behavior'
        from 'Clone a Git repository over HTTPS' to UseCases::'Retrieve and verify software'::'Retrieve through source TLS';
}
