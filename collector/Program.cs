using System.Text;

namespace LibreHardwareMonitorCollector;

public static class Program
{
    public static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        Console.Error.WriteLine("LibreHardwareMonitor collector started.");
        try
        {
            var json = CollectorJson.Serialize(HardwareSnapshotReader.Collect());
            if (args.Length == 0)
            {
                Console.Out.WriteLine(json);
                return 0;
            }
            if (args.Length == 2 && args[0] == "--inventory")
            {
                Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[1]))!);
                File.WriteAllText(args[1], json, new UTF8Encoding(false));
                return 0;
            }
            Console.Error.WriteLine("Usage: LibreHardwareMonitorCollector [--inventory <path>]");
            return 2;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine($"LibreHardwareMonitor collector failed: {error}");
            return 1;
        }
    }
}
