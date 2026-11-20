import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.omg.sysml.interactive.SysMLInteractive;

// Small adapter to the official parser and exporter; this is not a SysML parser.
public class ExportModel {
    public static void main(String[] args) throws Exception {
        if (args.length != 4) throw new IllegalArgumentException("library model package output.json");
        var engine = SysMLInteractive.getInstance();
        engine.loadLibrary(args[0]);
        var result = engine.process(Files.readString(Path.of(args[1])));
        System.err.println(result);
        if (result.hasErrors()) System.exit(1);
        var exported = engine.export(args[2], List.of());
        if (!(exported instanceof com.google.gson.JsonElement json)) {
            throw new IllegalStateException(String.valueOf(exported));
        }
        Files.createDirectories(Path.of(args[3]).toAbsolutePath().getParent());
        Files.writeString(Path.of(args[3]), json.toString());
    }
}
