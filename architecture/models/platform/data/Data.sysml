package DataDesign {
    doc /*
       Mapped storage provider. Local disks and an optional storage fabric are distinct choices. Detailed
       storage design remains in docs/01-architecture/06-data. This is a map to the existing shared
       identity, not a new component or detailed implementation claim.
    */
    public import Platform::platform::'Local guest-disk service';
}
