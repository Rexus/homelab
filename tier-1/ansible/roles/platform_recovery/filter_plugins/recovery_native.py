"""Compare accepted immutable Job inputs while allowing native API dictionary defaults."""


def recovery_spec_contains(actual, expected):
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(key in actual and recovery_spec_contains(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        return all(recovery_spec_contains(value, expected[index]) for index, value in enumerate(actual))
    return actual == expected


class FilterModule:
    def filters(self):
        return {'recovery_spec_contains': recovery_spec_contains}
