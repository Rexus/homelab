"""Keep requester-controlled Orca HTTP outside the promotion authority boundary.

The optional JVM check compiles the pinned upstream URL guard unchanged and binds
the rendered YAML with Spring Boot. Supply SPINNAKER_UPSTREAM_CACHE,
SPINNAKER_HTTP_TEST_CLASSPATH and SPINNAKER_HTTP_TEST_JAVA_HOME to run it offline.
"""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import jinja2
import yaml

from tier_repo_test_support import UPSTREAM


ROLE = UPSTREAM / "tier-1/ansible/roles/delivery_platform"
PIN = yaml.safe_load((ROLE / "files/software.yml").read_text())["spinnaker_revision"]
CACHE = os.environ.get("SPINNAKER_UPSTREAM_CACHE")
JAVA_HOME = os.environ.get("SPINNAKER_HTTP_TEST_JAVA_HOME")
CLASSPATH = os.environ.get("SPINNAKER_HTTP_TEST_CLASSPATH")


def render_orca(mode="flux"):
    environment = jinja2.Environment(undefined=jinja2.StrictUndefined)
    environment.filters["to_json"] = json.dumps
    template = environment.from_string((ROLE / "templates/spinnaker/service.yml.j2").read_text())
    return template.render(
        spinnaker_native_service="orca", spinnaker_native_sql_services=["orca"],
        delivery_platform_spinnaker_namespace="spinnaker",
        delivery_platform_spinnaker_delivery_mode=mode,
    )


# The probe uses the exact native webhook registration condition. The URL guard
# itself is compiled from the accepted upstream checkout, without substitutions.
HARNESS = r"""
import java.nio.file.Path;
import java.util.List;
import org.springframework.beans.factory.config.YamlPropertiesFactoryBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.bind.Bindable;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.context.properties.source.ConfigurationPropertySources;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.PropertiesPropertySource;
import org.springframework.core.io.FileSystemResource;
import com.netflix.spinnaker.orca.config.UserConfiguredUrlRestrictions;

public class OrcaHttpBoundary {
  @Configuration(proxyBeanMethods = false)
  @ConditionalOnProperty(prefix = "webhook.stage", value = "enabled", matchIfMissing = true)
  static class WebhookProbe {
    @Bean String requestControlledHttp() { return "enabled"; }
  }

  public static void main(String[] args) {
    var yaml = new YamlPropertiesFactoryBean();
    yaml.setResources(new FileSystemResource(Path.of(args[0])));
    var properties = new PropertiesPropertySource("rendered-orca", yaml.getObject());
    var builder = new UserConfiguredUrlRestrictions.Builder();
    new Binder(ConfigurationPropertySources.from(properties)).bind(
        "user-configured-url-restrictions", Bindable.ofInstance(builder));
    var restrictions = builder.build();
    if (!restrictions.getAllowedHostnames().pattern().isEmpty()) {
      throw new AssertionError("Spring did not bind the empty requester URL allowlist");
    }
    System.out.println("NATIVE_URL_CONFIG_BOUND");

    var urls = List.of(
        "https://fiat.spinnaker.svc:7003/roles/requester",
        "https://fiat.spinnaker.svc.cluster.local:7003/roles/requester",
        "https://orca.spinnaker.svc:8083/pipelines/execution/stages/approval",
        "https://gate.spinnaker.svc:8084/api/v1/pipelines/start",
        "http://169.254.169.254/latest/meta-data/",
        "https://127.0.0.1:7003/roles/requester",
        "https://[::1]:7003/roles/requester",
        "https://approved.example.test/redirect-to-fiat");
    for (String url : urls) {
      try {
        restrictions.validateURI(url);
        throw new AssertionError("Requester URL was accepted: " + url);
      } catch (IllegalArgumentException error) {
        // This native error precedes DNS resolution and the HTTP request. It also
        // prevents a permitted first request from redirecting into private services.
        if (!error.getMessage().startsWith("Allowed Hostnames are not set")) {
          throw new AssertionError("URL reached another validation phase: " + url, error);
        }
      }
    }
    System.out.println("NATIVE_URL_GUARD_PASSED " + urls.size());
    try (var context = new AnnotationConfigApplicationContext()) {
      context.getEnvironment().getPropertySources().addFirst(properties);
      context.register(WebhookProbe.class);
      context.refresh();
      if (context.containsBean("requestControlledHttp")) {
        throw new AssertionError("The native webhook registration condition remained enabled");
      }
    }
    System.out.println("NATIVE_HTTP_BOUNDARY_PASSED " + urls.size());
  }
}
"""


class SpinnakerHttpBoundary(unittest.TestCase):
    def test_flux_blocks_requester_http_and_retains_native_execution(self):
        configuration = yaml.safe_load(render_orca())
        self.assertIs(configuration["webhook"]["stage"]["enabled"], False)
        self.assertIs(configuration["webhook"]["allowedRequestsEnabled"], True)
        self.assertEqual(configuration["webhook"]["allowedRequests"], [])
        self.assertEqual(configuration["user-configured-url-restrictions"]["allowed-hostnames-regex"], "")
        self.assertIs(configuration["sql"]["enabled"], True)
        self.assertIs(configuration["tasks"]["useManagedServiceAccounts"], True)

    def test_direct_delivery_preserves_its_existing_stage_configuration(self):
        configuration = yaml.safe_load(render_orca("direct"))
        self.assertNotIn("webhook", configuration)
        self.assertNotIn("user-configured-url-restrictions", configuration)

    def test_promotion_approval_dependencies_only_use_local_expressions_and_jobs(self):
        environment = jinja2.Environment(undefined=jinja2.StrictUndefined)
        environment.filters["to_json"] = json.dumps
        template_path = UPSTREAM / "tier-1/pipelines/flux-promotion.yml.j2"
        template = environment.from_string(template_path.read_text())
        for mode in ("promote", "rollback"):
            with self.subTest(mode=mode):
                pipeline = yaml.safe_load(template.render(
                    delivery_promotion_pipeline_ids={mode: "fixture-pipeline"},
                    delivery_promotion_mode=mode, delivery_promotion_application="fixture",
                    delivery_promotion_approver_role="fixture-approvers",
                    delivery_promotion_timeout_seconds=900,
                    delivery_promotion_worker_image="registry.example.test/client@sha256:" + "a" * 64,
                    delivery_promotion_authority_url=(
                        "https://delivery-promotion-authority.delivery-promotion-authority.svc:8443"),
                ))
                self.assertEqual([stage["type"] for stage in pipeline["stages"]],
                                 ["runJobManifest", "manualJudgment", "checkPreconditions", "runJobManifest"])
                expression = pipeline["stages"][2]["preconditions"][0]
                self.assertEqual(expression["type"], "expression")
                self.assertNotRegex(expression["context"]["expression"],
                                    r"#(?:fromUrl|jsonFromUrl|yamlFromUrl|propertiesFromUrl)\(")
                for stage in (pipeline["stages"][0], pipeline["stages"][3]):
                    self.assertEqual(stage["manifest"]["metadata"]["namespace"], "delivery-promotion")

    @unittest.skipUnless(CACHE and JAVA_HOME and CLASSPATH,
                         "Requires retained pinned Spinnaker source, native JDK and Spring/Lombok dependencies")
    def test_native_spring_binding_disables_webhooks_and_rejects_internal_urls_before_dns(self):
        cache = Path(CACHE)
        revision = subprocess.run(["git", "-C", str(cache), "rev-parse", "HEAD"],
                                  capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(revision, PIN)
        relative = ("orca/orca-webhook/src/main/java/com/netflix/spinnaker/orca/webhook/"
                    "config/WebhookConfiguration.java")
        webhook_source = (cache / relative).read_text()
        self.assertIn('@ConditionalOnProperty(prefix = "webhook.stage", value = "enabled", matchIfMissing = true)',
                      webhook_source)
        self.assertIn('@ComponentScan("com.netflix.spinnaker.orca.webhook")', webhook_source)
        core = cache / "orca/orca-core/src/main/java/com/netflix/spinnaker/orca"
        helper = (core / "pipeline/expressions/functions/UrlExpressionFunctionProvider.java").read_text()
        self.assertIn("helperFunctionUrlRestrictions.get().validateURI(url)", helper)
        self.assertIn("return readJson(fromUrl(url))", helper)
        self.assertIn("return readYaml(fromUrl(url))", helper)
        self.assertIn("return readProperties(fromUrl(url))", helper)
        # HTTP-valued expression preconditions use the same ContextParameterProcessor
        # as ordinary SpEL fields. The required local precondition remains enabled.
        precondition = (core / "pipeline/tasks/ExpressionPreconditionTask.java").read_text()
        self.assertIn("contextParameterProcessor.process(", precondition)

        with tempfile.TemporaryDirectory(prefix="spinnaker-http-guard-") as directory:
            working = Path(directory)
            (working / "OrcaHttpBoundary.java").write_text(HARNESS)
            (working / "orca.yml").write_text(render_orca())
            result = subprocess.run(
                [str(Path(JAVA_HOME) / "bin/javac"), "-classpath", CLASSPATH,
                 "-processorpath", CLASSPATH, "-d", str(working),
                 str(core / "config/UserConfiguredUrlRestrictions.java"),
                 str(working / "OrcaHttpBoundary.java")], capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run(
                [str(Path(JAVA_HOME) / "bin/java"), "-classpath", str(working) + os.pathsep + CLASSPATH,
                 "OrcaHttpBoundary", str(working / "orca.yml")],
                capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("NATIVE_HTTP_BOUNDARY_PASSED 8", result.stdout)
