. as $log
| [
    range(0; $log | length) as $i
    | $log[$i]
    | select(.type == "assistant" and .parent_tool_use_id == null)
    | .message.content[]?
    | select(.type == "tool_use" and .name == "Skill")
    | select((.input.skill // .input.name // "") == "security-review")
    | {id, index: $i}
  ] as $calls
| [
    range(0; $log | length) as $i
    | $log[$i]
    | select(.type == "assistant")
    | .message.content[]?
    | select(.type == "tool_use" and (.name == "Agent" or .name == "Task"))
    | {id, index: $i, input, parent: $log[$i].parent_tool_use_id}
  ] as $delegates
| if ($calls | length) != 1 then false
  else
    (
      [
        range(($calls[0].index + 1); ($log | length)) as $i
        | $log[$i]
        | select(.type == "user" and .parent_tool_use_id == null)
        | .message.content[]?
        | select(
            .type == "tool_result"
            and .tool_use_id == $calls[0].id
            and (.is_error != true)
          )
      ] | length == 1
    )
    and ($delegates | length > 0)
    and (($delegates | map(.id) | unique | length) == ($delegates | length))
    and all($delegates[];
      . as $delegate
      | (.id | type == "string" and length > 0)
        and .input.subagent_type == "security-review-reader"
        and (.input.run_in_background // false) == false
        and ([
          range(($delegate.index + 1); ($log | length)) as $i
          | $log[$i]
          | select(.type == "user" and .parent_tool_use_id == $delegate.parent)
          | .message.content[]?
          | select(.type == "tool_result" and .tool_use_id == $delegate.id)
          | {result: ., index: $i}
        ] as $results
        | ($results | length == 1)
          and ($results[0].result | .is_error != true)
          and ($results[0].result
            | (.content | type == "string" and test("\\S"))
              or (.content | type == "array" and length > 0
                  and all(.[]; .type == "text" and (.text | test("\\S")))))
          and ($log[($results[0].index + 1):] | any(.[]; .type == "result")))
    )
    and (
      $log | [.[] | select(.type == "result")] | last
      | .subtype == "success" and .is_error == false
        and (
          .result | fromjson
          | .status == "completed"
            and .base_sha == $base and .head_sha == $head
            and (.findings | type == "array")
            and all(.findings[]; type == "string" and test("\\S"))
        )
    )
  end
