// Copyright 2015 The Oppia Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * @fileoverview Factory for creating new frontend instances of State
 * domain objects.
 *
 * @author sean@seanlip.org (Sean Lip)
 */

oppia.factory('StateObjectFactory', [
    'INTERACTION_SPECS', 'INTERACTION_DISPLAY_MODE_INLINE',
    function(INTERACTION_SPECS, INTERACTION_DISPLAY_MODE_INLINE) {

  function State(name, content, interaction, paramChanges) {
    this.name = name;
    this.content = content;
    this.interaction = interaction;
    this.paramChanges = paramChanges;
  }

  // Instance methods.
  State.prototype.toBackendDict = function() {
    return {
      content: this.content,
      interaction: this.interaction,
      param_changes: this.paramChanges
    };
  };

  // Static class methods. Note that "this" is not available in
  // static contexts.
  State.create = function(stateName, stateDict) {
    return new State(
      stateName,
      stateDict.content,
      stateDict.interaction,
      stateDict.param_changes);
  };

  return State;
}]);
