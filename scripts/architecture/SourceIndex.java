import java.nio.file.Files;
import java.nio.file.Path;
import com.google.gson.*;
import org.eclipse.xtext.nodemodel.util.NodeModelUtils;
import org.eclipse.xtext.resource.XtextResource;
import org.omg.sysml.interactive.SysMLInteractive;
import org.omg.sysml.lang.sysml.Element;

// Syntax locations come from the official parser. No text grammar is reimplemented here.
public class SourceIndex {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("source.sysml output.json");
        String source = Files.readString(Path.of(args[0])).replace("\r\n", "\n").replace('\r', '\n');
        var engine = SysMLInteractive.getInstance();
        engine.setResource("return-source.sysml");
        engine.parse(source);
        var resource = (XtextResource) engine.getResource();
        var result = new JsonObject();
        var elements = new JsonArray();
        var errors = new JsonArray();
        for (var error : resource.getParseResult().getSyntaxErrors()) {
            var row = new JsonObject();
            row.addProperty("start", source.codePointCount(0, error.getOffset()));
            row.addProperty("end", source.codePointCount(0, error.getEndOffset()));
            row.addProperty("message", error.getSyntaxErrorMessage().getMessage());
            errors.add(row);
        }
        var iterator = resource.getAllContents();
        while (iterator.hasNext()) {
            var object = iterator.next();
            if (!(object instanceof Element element)) continue;
            var node = NodeModelUtils.findActualNodeFor(element);
            if (node == null) continue;
            var row = new JsonObject();
            row.addProperty("key", element.getDeclaredShortName());
            row.addProperty("name", element.getDeclaredName());
            row.addProperty("kind", element.eClass().getName());
            if (element.eClass().getName().equals("Package")) {
                var parts = new java.util.ArrayList<String>();
                for (Element cursor = element; cursor != null; cursor = cursor.getOwner()) {
                    if (cursor.getDeclaredName() != null) parts.add(0, cursor.getDeclaredName());
                }
                row.addProperty("qualified_name", String.join("::", parts));
            }
            row.addProperty("start", source.codePointCount(0, node.getOffset()));
            row.addProperty("end", source.codePointCount(0, node.getEndOffset()));
            elements.add(row);
        }
        result.add("elements", elements);
        result.add("errors", errors);
        Files.writeString(Path.of(args[1]), new GsonBuilder().setPrettyPrinting().create().toJson(result));
    }
}
