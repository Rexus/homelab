package FunctionalRequirements {
    requirement <'REQ-policy'> admittedSources {
        subject proxy : PolicyProxy;
        require constraint {
            doc /* Remote access requires the accepted client, destination and port policy; otherwise deny. */
        }
    }
    satisfy requirement <'SAT-policy'> policySatisfied references admittedSources
        by context.'Policy proxy / HTTP cache' {
        doc /* Design assertion for the selected policy proxy; verification and site evidence are separate. */
    }
    dependency <'DEP-policy'> 'Admission obligation' from PolicyProxy to admittedSources;
}
