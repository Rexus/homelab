package AdmissionAnalysis {
    private import AdmissionLogic::*;
    calc def <'CALC-shortcut'> CacheShortcut {
        doc /* Rejected candidate: a warm cache must not bypass admission. An analysis alternative, not an implementation. */
        in clientAllowed : ScalarValues::Boolean;
        in destinationAllowed : ScalarValues::Boolean;
        in portAllowed : ScalarValues::Boolean;
        in cacheHit : ScalarValues::Boolean;
        return admitted : ScalarValues::Boolean = cacheHit or AdmissionAllowed(clientAllowed, destinationAllowed, portAllowed);
    }
    analysis def <'AN-admission'> AdmissionOrderReview {
        subject proxy : PolicyProxy;
        objective { doc /* Find whether a proposed cache shortcut admits requests rejected by the policy predicate. */ }
        in clientAllowed : ScalarValues::Boolean;
        in destinationAllowed : ScalarValues::Boolean;
        in portAllowed : ScalarValues::Boolean;
        in cacheHit : ScalarValues::Boolean;
        return counterexample : ScalarValues::Boolean =
            CacheShortcut(clientAllowed, destinationAllowed, portAllowed, cacheHit) and
            not AdmissionAllowed(clientAllowed, destinationAllowed, portAllowed);
    }
    dependency <'AN-policy'> 'Evaluates admission obligation' from AdmissionOrderReview to admittedSources;
    dependency <'AN-function'> 'Evaluates admission function' from AdmissionOrderReview to Functions::'F-admit';
}
