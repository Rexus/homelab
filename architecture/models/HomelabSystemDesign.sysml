package SystemDesign {
    doc /* System Overall composes design boundaries. Only software intake is traced end to end.
           Other subsystem responsibilities are mapped from existing architecture chapters. */
    part def <'SYS-DEF-system'> HomelabSystem;
    part def <'SYS-DEF-intake'> SoftwareIntakeSubsystem;
    part def <'SYS-DEF-trust'> TrustAndAccess;
    part def <'SYS-DEF-delivery'> DeliveryAndWorkloads;
    part def <'SYS-DEF-operations'> OperationsAndRecovery;
    part <'SYS-homelab'> homelab : HomelabSystem {
        part <'SYS-intake'> 'Software intake' : SoftwareIntakeSubsystem {
            ref part <'SYS-intake-proxy'> proxy : ProxyDesign::PolicyProxy = Context::context.'Policy proxy / HTTP cache';
            ref part <'SYS-intake-cache'> cache : CacheDesign::DisposableCache = Context::context.'Rebuildable cache storage';
        }
        ref part <'SYS-platform'> 'Shared platform' = Platform::platform;
        part <'SYS-trust'> 'Trust and access' : TrustAndAccess {
            doc /* Mapped boundary: cryptography, independent key custody and identity/access.
                   Offline custody is not implicitly hosted by the connected platform. */
        }
        part <'SYS-delivery'> 'Delivery and workloads' : DeliveryAndWorkloads {
            doc /* Mapped boundary: reviewed source, builds, artifacts and scoped workload delivery. */
        }
        part <'SYS-operations'> 'Operations and recovery' : OperationsAndRecovery {
            doc /* Mapped boundary: observation, protected evidence, maintenance and recovery.
                   Dependency on managed resources does not allocate independent recovery custody. */
        }
        dependency <'SYS-intake-resources'> 'Execution / storage / network'
            from 'Software intake' to 'Shared platform';
        dependency <'SYS-delivery-supply'> 'Controlled acquisition'
            from 'Delivery and workloads' to 'Software intake';
        dependency <'SYS-delivery-trust'> 'Identity / trust'
            from 'Delivery and workloads' to 'Trust and access';
        dependency <'SYS-operations-resources'> 'Managed resources'
            from 'Operations and recovery' to 'Shared platform';
    }
}
