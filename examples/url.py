
from rebuild.builder import *


# Disclaimer: This will not detect every legal url

pat = force_full(
    # Protocol
    capture_as("protocol", one_or_more(letter()))
    + literally("://")

    # Domain
    + capture_as(
        "domain",
        one_or_more(letter())
        + one_or_more(either(letter(), literally(".")))
        + at_least_n_times(2, letter())
    )

    # Port
    + optionally(literally(":") + capture_as("port", one_or_more(digit())))

    # Path, make it non greedy, so that it does not consume the parameters, too
    + optionally(capture_as("path", literally("/") + zero_or_more(anything(), greedy=False)))
    + either(literally("?"), must_end())

    # Parameters
    + optionally(capture_as("parameters", zero_or_more(anything())))
)

print(pat)

# Generates:
# ^(?P<protocol>[a-zA-Z]+)://(?P<domain>[a-zA-Z]+[a-zA-Z\.]+[a-zA-Z]{2,})(?::(?P<port>\d+))?(?P<path>/.*?)?(?:\?|$)(?P<parameters>.*)?$
