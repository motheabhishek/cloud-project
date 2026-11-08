# Subnet allocation for 10.20.0.0/16

Rule: usable hosts = 2^(32 - prefix) - 2. Allocate from the largest requirement to the smallest, starting at 10.20.0.0, each subnet right after the previous one, using the smallest prefix that fits.

## Working
- app, 1,000 hosts: /23 gives 510 (too few), /22 gives 1,022. Use /22.
- public, 250 hosts: /25 gives 126 (too few), /24 gives 254. Use /24.
- data, 100 hosts: /26 gives 62 (too few), /25 gives 126. Use /25.
- management, 20 hosts: /28 gives 14 (too few), /27 gives 30. Use /27.

## Table

| Subnet | Hosts needed | Network address | Prefix | Usable host range | Broadcast address | Usable hosts |
|---|---|---|---|---|---|---|
| app | 1,000 | 10.20.0.0 | /22 | 10.20.0.1 - 10.20.3.254 | 10.20.3.255 | 1,022 |
| public | 250 | 10.20.4.0 | /24 | 10.20.4.1 - 10.20.4.254 | 10.20.4.255 | 254 |
| data | 100 | 10.20.5.0 | /25 | 10.20.5.1 - 10.20.5.126 | 10.20.5.127 | 126 |
| management | 20 | 10.20.5.128 | /27 | 10.20.5.129 - 10.20.5.158 | 10.20.5.159 | 30 |

## Why the NACL is stateless and rule order matters
A NACL does not remember connections, so every packet is checked on its own. Replies need their own allow rule: inbound replies from the app subnet (TCP 1024-65535, rule 140) and outbound replies to clients (TCP 1024-65535, outbound rule 110).

Rules are checked from the lowest number upward and the first match wins. The deny for 198.51.100.0/24 is rule 100, lower than the allows for TCP 80 and 443 (rules 110 and 120). If the deny had a higher number, the allow would match first and the abusive range would get through on web ports.
