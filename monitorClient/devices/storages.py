import subprocess
import plistlib
import pandas as pd
import numpy as np

def _DictFromSubprocess(command, stdin=None):
    """returns a dict based upon a subprocess call with a -plist argument.
    Args:
        command: the command to be executed as a list
        stdin: any standard input required.
    Returns:
        dict: dictionary from command output
    Raises:
        Exception: Error running command
        Exception: Error creating plist from standard output
    """

    task = {}

    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate()

    if p.returncode != 0:
        raise Exception("Error running command: %s, stderr: %s" %
                                             (command, stderr))
    else:
        # try:
        return plistlib.loads(stdout)
        # except:
        #     raise Exception("Error creating plist from output: %s" % stdout)

def _DictFromDiskutilList():
    """Calls diskutil list -plist and returns as dict."""
    command = ["/usr/sbin/diskutil", "list", "-plist"]
    return _DictFromSubprocess(command)

def _DictFromDiskutilInfo(deviceid):
    """Calls diskutil info for a specific device id.
    Args:
        deviceid: a given device id for a disk like object
    Returns:
        info: dictionary from resulting plist output
    """
    command = ["/usr/sbin/diskutil", "info", "-plist", deviceid]
    return _DictFromSubprocess(command)

def AllDisksAndPartitions():
    """Returns list of all disks and partitions."""
    try:
        return _DictFromDiskutilList()["AllDisksAndPartitions"]
    except KeyError:
        # TODO(user): fix errors to actually provide info...
        raise Exception("Unable to list all partitions.")

def get_connected_drives(content_blacklist=["Apple_HFS"]):
    """Returns a pandas dataframe with all USB drives connected"""
    all_disks = pd.DataFrame(AllDisksAndPartitions())
    all_partitions = []
    for row in all_disks[all_disks.Content.isin(["GUID_partition_scheme", "FDisk_partition_scheme"])].explode("Partitions").to_dict(orient="records"):
        new_row = {}
        new_row["PartitionScheme"] = row["Content"]
        new_row["MainDeviceIdentifier"] = row["DeviceIdentifier"]
        new_row["MainDeviceSize"] = row["Size"]
        new_row.update(row["Partitions"])
        all_partitions.append(new_row)

    all_partitions = pd.DataFrame(all_partitions)
    all_partitions = all_partitions.dropna(subset=["MountPoint"])
    all_partitions = all_partitions.replace({np.nan: None})

    return all_partitions[~all_partitions.Content.isin(content_blacklist)]