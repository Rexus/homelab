package ExecutionTrace {
    dependency <'EXEC-refines'> 'Executable refinement' from RetrievalExecution::Retrieve to Behavior::HttpRetrieval;
    dependency <'EXEC-H-request'> from RetrievalExecution::Retrieve::'X-request' to 'Behavior'::'B-HTTP'::'H-request';
    dependency <'EXEC-H-check'> from RetrievalExecution::Retrieve::'X-check' to 'Behavior'::'B-HTTP'::'H-check';
    dependency <'EXEC-H-lookup'> from RetrievalExecution::Retrieve::'X-lookup' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-lookup';
    dependency <'EXEC-H-cached'> from RetrievalExecution::Retrieve::'X-cached' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-hit'::'H-cached';
    dependency <'EXEC-H-fetch'> from RetrievalExecution::Retrieve::'X-fetch' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-fetch';
    dependency <'EXEC-H-origin'> from RetrievalExecution::Retrieve::'X-origin' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-ok'::'H-origin';
    dependency <'EXEC-H-cache-rules'> from RetrievalExecution::Retrieve::'X-cache-rules' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-ok'::'H-cache-rules';
    dependency <'EXEC-H-response'> from RetrievalExecution::Retrieve::'X-response' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-ok'::'H-response';
    dependency <'EXEC-H-verify'> from RetrievalExecution::Retrieve::'X-verify' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-has-content'::'H-verify';
    dependency <'EXEC-H-accepted'> from RetrievalExecution::Retrieve::'X-accepted' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-has-content'::'H-integrity-choice'::'H-trust-ok'::'H-accepted';
    dependency <'EXEC-H-rejected'> from RetrievalExecution::Retrieve::'X-rejected' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-has-content'::'H-integrity-choice'::'H-trust-failed'::'H-rejected';
    dependency <'EXEC-H-denied'> from RetrievalExecution::Retrieve::'X-denied' to 'Behavior'::'B-HTTP'::'H-policy'::'H-deny'::'H-denied';
    dependency <'EXEC-H-source-failure'> from RetrievalExecution::Retrieve::'X-source-failure' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-down'::'H-source-failure';
    dependency <'EXEC-H-unavailable'> from RetrievalExecution::Retrieve::'X-unavailable' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-down'::'H-unavailable';
    dependency <'EXEC-H-stop'> from RetrievalExecution::Retrieve::'X-stop' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-no-content'::'H-stop';
    dependency <'EXEC-RUN-miss'> from RetrievalRuns::'RUN-miss' to UseCases::'UC-update'::'SC-http-miss';
    dependency <'EXEC-RUN-hit-offline'> from RetrievalRuns::'RUN-hit-offline' to UseCases::'UC-update'::'SC-http-hit';
    dependency <'EXEC-RUN-denied'> from RetrievalRuns::'RUN-denied' to UseCases::'UC-update'::'SC-http-denied';
    dependency <'EXEC-RUN-source-failure'> from RetrievalRuns::'RUN-source-failure' to UseCases::'UC-update'::'SC-http-source-failure';
    dependency <'EXEC-RUN-untrusted'> from RetrievalRuns::'RUN-untrusted' to UseCases::'UC-update'::'SC-http-untrusted';
    dependency <'EXEC-RUN-cache-untrusted'> from RetrievalRuns::'RUN-cache-untrusted' to UseCases::'UC-update'::'SC-http-cache-untrusted';
}
