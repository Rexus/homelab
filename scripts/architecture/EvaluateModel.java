import java.nio.file.Files;
import java.nio.file.Path;
import org.omg.sysml.interactive.SysMLInteractive;
import com.google.gson.JsonObject;

public class EvaluateModel {
    public static void main(String[] args) throws Exception {
        if (args.length != 4) throw new IllegalArgumentException("library model queries.json output.json");
        var engine = SysMLInteractive.getInstance();
        engine.loadLibrary(Path.of(args[0]).toAbsolutePath().toString());
        var result = engine.process(Files.readString(Path.of(args[1])));
        if (result.hasErrors()) throw new IllegalStateException(result.toString());
        var queries = com.google.gson.JsonParser.parseString(Files.readString(Path.of(args[2]))).getAsJsonObject();
        var answers = new JsonObject();
        for (var entry : queries.entrySet()) {
            var value = engine.eval(entry.getValue().getAsString(), "SoftwareIntake::AdmissionAnalysis").trim();
            var match = java.util.regex.Pattern.compile("LiteralBoolean (true|false) \\([^\\n]+\\)").matcher(value);
            if (!match.matches())
                throw new IllegalStateException(entry.getKey() + ": " + value);
            answers.addProperty(entry.getKey(), Boolean.parseBoolean(match.group(1)));
        }
        Files.writeString(Path.of(args[3]), answers.toString());
    }
}
