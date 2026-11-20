package AdmissionLogic {
    calc def <'CALC-admission'> AdmissionAllowed {
        in clientAllowed : ScalarValues::Boolean;
        in destinationAllowed : ScalarValues::Boolean;
        in portAllowed : ScalarValues::Boolean;
        return admitted : ScalarValues::Boolean = clientAllowed and destinationAllowed and portAllowed;
    }
}
