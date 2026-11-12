SeeUat4 - Security Notes
========================

Purpose
-------
SeeUat4 blocks configured domains using the Windows Hosts file.

Code signing
------------
PowerShell scripts are signed using the SeeUat4 self-signed
code-signing certificate.

Certificate subject:
CN=SeeUat4 Code Signing

Thumbprint:
7FD847AE81E88BDD44B26105C189432267E33741

Execution policy
----------------
The project uses AllSigned in dedicated PowerShell processes.

The Windows default execution policy is not changed.

Administrator privileges
------------------------
Applying the Hosts-file block requires an elevated PowerShell
session.

Backup
------
The original Hosts file is stored at:

state/hosts.original.bak

Do not overwrite this backup with a blocked Hosts file.

Release
-------
The release procedure is under development.

SeeUat4 is a self-control mechanism, not tamper-proof security.
A local administrator can potentially bypass its protections.