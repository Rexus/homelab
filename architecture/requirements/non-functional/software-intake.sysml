package QualityRequirements {
    requirement <'REQ-integrity'> consumerVerification {
        subject client : UpdateClient;
        require constraint {
            doc /* Preserve source TLS through CONNECT and consumer verification. Cache presence is not approval. */
        }
    }
    requirement <'REQ-custody'> independentRecovery {
        subject cache : DisposableCache;
        require constraint {
            doc /* Losing rebuildable cache data must not erase the independently retained recovery supply. */
        }
    }
    requirement <'REQ-egress'> noBypass {
        subject client : UpdateClient;
        require constraint {
            doc /* Independently enforce the accepted network egress policy. Proxy configuration alone cannot deny bypass. */
        }
    }
    dependency <'DEP-integrity'> 'Verification obligation' from UpdateClient to consumerVerification;
    dependency <'DEP-custody'> 'Recovery separation' from DisposableCache to independentRecovery;
    dependency <'DEP-egress'> 'Network obligation' from UpdateClient to noBypass;
}
