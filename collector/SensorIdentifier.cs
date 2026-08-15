using System.Text;

namespace LibreHardwareMonitorCollector;

public static class SensorIdentifier
{
    public static string MakeUnique(string libraryIdentifier, string sensorName, ISet<string> usedIdentifiers)
    {
        if (usedIdentifiers.Add(libraryIdentifier))
            return libraryIdentifier;

        var suffix = new string(sensorName
            .Trim()
            .ToLowerInvariant()
            .Select(character => char.IsLetterOrDigit(character) ? character : '-')
            .ToArray())
            .Trim('-');
        var candidate = $"{libraryIdentifier}~{suffix}";
        var number = 2;
        while (!usedIdentifiers.Add(candidate))
            candidate = $"{libraryIdentifier}~{suffix}-{number++}";
        return candidate;
    }
}
