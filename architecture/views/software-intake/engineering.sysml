package EngineeringViews {
    viewpoint def <'VP-engineering'> EngineeringRelationships {
        require constraint { doc /* Show which intent shapes the design, distinguish allocation from satisfaction and verification, and expose evidence gaps. */ }
    }
    view <'VIEW-engineering'> 'Engineering relationships' : StandardViewDefinitions::GeneralView {
        viewpoint : EngineeringRelationships;
        expose UseCases::'UC-update';
        expose FunctionalRequirements::admittedSources;
        expose FunctionalRequirements::policySatisfied;
        expose Functions::'F-admit';
        expose Functions::'F-http';
        expose Functions::'ALLOC-F-admit-0';
        expose Functions::'ALLOC-F-http-0';
        expose Context::context::'Policy proxy / HTTP cache';
        expose Verification::*;
        expose QualityRequirements::*;
        expose AdmissionAnalysis::*;
    }
}
